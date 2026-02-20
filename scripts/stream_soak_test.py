#!/usr/bin/env python3
"""
Stream/Ring soak test runner.

Purpose:
- reproduce long-running stutter/hang behavior
- exercise concurrent clients per camera
- track CPU/memory trends and request error rates
"""

import argparse
import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


PRESETS = {
    "quick": 15 * 60,
    "6h": 6 * 60 * 60,
    "12h": 12 * 60 * 60,
}


class HttpClient:
    def __init__(self, base_url: str, timeout: float, api_key: str = ""):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.api_key = api_key.strip()

    def _headers(self, content_type: bool = False) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "smarthome-soak-test/1.0",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get_json(self, path: str, query: Optional[Dict[str, str]] = None) -> Tuple[int, Dict]:
        if query:
            qs = urlencode(query)
            path = f"{path}?{qs}"
        req = Request(urljoin(self.base_url, path.lstrip("/")), headers=self._headers())
        with urlopen(req, timeout=self.timeout) as resp:
            code = int(resp.getcode() or 0)
            body = resp.read().decode("utf-8", errors="replace")
            return code, json.loads(body) if body else {}

    def post_json(self, path: str, payload: Optional[Dict] = None) -> Tuple[int, Dict]:
        body = json.dumps(payload or {}).encode("utf-8")
        req = Request(
            urljoin(self.base_url, path.lstrip("/")),
            data=body,
            headers=self._headers(content_type=True),
            method="POST",
        )
        with urlopen(req, timeout=self.timeout) as resp:
            code = int(resp.getcode() or 0)
            raw = resp.read().decode("utf-8", errors="replace")
            return code, json.loads(raw) if raw else {}

    def get_text(self, path: str) -> Tuple[int, str]:
        req = Request(urljoin(self.base_url, path.lstrip("/")), headers={"User-Agent": "smarthome-soak-test/1.0"})
        with urlopen(req, timeout=self.timeout) as resp:
            code = int(resp.getcode() or 0)
            return code, resp.read().decode("utf-8", errors="replace")

    def get_bytes(self, path: str) -> Tuple[int, bytes]:
        req = Request(urljoin(self.base_url, path.lstrip("/")), headers={"User-Agent": "smarthome-soak-test/1.0"})
        with urlopen(req, timeout=self.timeout) as resp:
            code = int(resp.getcode() or 0)
            return code, resp.read()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run stream/ring soak tests.")
    p.add_argument("--base-url", default="http://127.0.0.1:5000", help="Web HMI base URL")
    p.add_argument("--api-key", default=os.getenv("SMARTHOME_ADMIN_API_KEY", ""), help="Optional X-API-Key")
    p.add_argument("--preset", choices=sorted(PRESETS.keys()), default="quick", help="Duration preset")
    p.add_argument("--duration-seconds", type=int, default=0, help="Override preset duration")
    p.add_argument("--clients-per-camera", type=int, default=3, help="Concurrent fetch workers per camera")
    p.add_argument("--request-timeout-seconds", type=float, default=5.0, help="HTTP timeout")
    p.add_argument("--poll-interval-seconds", type=float, default=1.0, help="Worker loop interval")
    p.add_argument("--monitor-interval-seconds", type=float, default=30.0, help="Resource monitor sample interval")
    p.add_argument("--camera-ids", default="", help="Comma separated camera IDs (default: auto-select)")
    p.add_argument("--include-rtsp", action="store_true", help="Include RTSP cameras")
    p.add_argument("--include-ring", action="store_true", help="Include Ring cameras")
    p.add_argument("--report-file", default="", help="Optional JSON report output path")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    return p.parse_args()


def choose_cameras(camera_map: Dict[str, Dict], wanted_ids: List[str], include_rtsp: bool, include_ring: bool) -> Dict[str, Dict]:
    if not include_rtsp and not include_ring:
        include_rtsp = True
        include_ring = True

    selected = {}
    for cam_id, cam in camera_map.items():
        cam_type = str(cam.get("type", "rtsp")).strip().lower()
        if wanted_ids and cam_id not in wanted_ids:
            continue
        if cam_type == "ring" and not include_ring:
            continue
        if cam_type != "ring" and not include_rtsp:
            continue
        selected[cam_id] = cam
    return selected


def parse_playlist_for_segment(playlist_text: str) -> Optional[str]:
    for line in playlist_text.splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        return item
    return None


def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except HTTPError as e:
        return None, f"http:{e.code}"
    except URLError as e:
        return None, f"url:{e.reason}"
    except Exception as e:
        return None, str(e)


def new_camera_stats() -> Dict:
    return {
        "requests_total": 0,
        "requests_failed": 0,
        "playlist_ok": 0,
        "segment_ok": 0,
        "stutter_events": 0,
        "last_success_ts": 0.0,
        "latency_ms_samples": [],
        "errors": {},
    }


def record_error(stats: Dict, err: str):
    stats["requests_failed"] += 1
    stats["errors"][err] = stats["errors"].get(err, 0) + 1


def run_worker(
    stop_event: threading.Event,
    client: HttpClient,
    cam_id: str,
    hls_url: str,
    stats: Dict,
    lock: threading.Lock,
    poll_interval: float,
):
    while not stop_event.is_set():
        start = time.time()
        with lock:
            stats["requests_total"] += 1

        playlist_result, err = safe_call(client.get_text, hls_url)
        if err:
            with lock:
                record_error(stats, f"playlist_{err}")
            time.sleep(poll_interval)
            continue

        _, playlist_text = playlist_result
        segment_rel = parse_playlist_for_segment(playlist_text)
        if not segment_rel:
            with lock:
                record_error(stats, "playlist_no_segment")
            time.sleep(poll_interval)
            continue

        segment_url = f"/static/hls/{segment_rel.split('/')[-1]}" if "://" not in segment_rel else segment_rel
        segment_result, err = safe_call(client.get_bytes, segment_url)
        if err:
            with lock:
                stats["playlist_ok"] += 1
                record_error(stats, f"segment_{err}")
            time.sleep(poll_interval)
            continue

        _, body = segment_result
        if not body:
            with lock:
                stats["playlist_ok"] += 1
                record_error(stats, "segment_empty")
            time.sleep(poll_interval)
            continue

        took_ms = (time.time() - start) * 1000.0
        with lock:
            stats["playlist_ok"] += 1
            stats["segment_ok"] += 1
            stats["last_success_ts"] = time.time()
            stats["latency_ms_samples"].append(round(took_ms, 2))
            if len(stats["latency_ms_samples"]) > 2000:
                stats["latency_ms_samples"] = stats["latency_ms_samples"][-2000:]

        elapsed = time.time() - start
        sleep_for = max(0.01, poll_interval - elapsed)
        time.sleep(sleep_for)


def summarize_latency(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"count": 0, "min_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    arr = sorted(samples)
    n = len(arr)
    p50 = arr[int(0.50 * (n - 1))]
    p95 = arr[int(0.95 * (n - 1))]
    return {
        "count": n,
        "min_ms": arr[0],
        "p50_ms": p50,
        "p95_ms": p95,
        "max_ms": arr[-1],
    }


def main():
    args = parse_args()
    random.seed(args.seed)
    started_at = time.time()
    duration_seconds = int(args.duration_seconds or PRESETS[args.preset])
    wanted_ids = [x.strip() for x in args.camera_ids.split(",") if x.strip()]
    client = HttpClient(args.base_url, timeout=args.request_timeout_seconds, api_key=args.api_key)

    code, cameras_resp = client.get_json("/api/cameras")
    if code != 200:
        raise RuntimeError(f"/api/cameras failed with {code}")
    camera_map = cameras_resp.get("cameras", {})
    if not camera_map:
        raise RuntimeError("No cameras configured")

    selected = choose_cameras(camera_map, wanted_ids, args.include_rtsp, args.include_ring)
    if not selected:
        raise RuntimeError("No matching cameras selected")

    print(f"Selected cameras: {', '.join(sorted(selected.keys()))}")
    print(f"Duration: {duration_seconds}s, clients_per_camera: {args.clients_per_camera}")

    # Start streams.
    running_targets = {}
    for cam_id, cam in selected.items():
        payload = {"use_substream": True} if str(cam.get("type", "rtsp")).lower() != "ring" else {}
        result, err = safe_call(client.post_json, f"/api/cameras/{cam_id}/start", payload)
        if err:
            raise RuntimeError(f"Start failed for {cam_id}: {err}")
        status_code, body = result
        if status_code != 200 or not body.get("success"):
            raise RuntimeError(f"Start failed for {cam_id}: {status_code} {body}")
        hls_url = body.get("hls_url") or f"/static/hls/{cam_id}.m3u8"
        running_targets[cam_id] = {
            "hls_url": hls_url,
            "type": str(cam.get("type", "rtsp")).lower(),
        }
        print(f"Started {cam_id} ({running_targets[cam_id]['type']}): {hls_url}")

    stop_event = threading.Event()
    stats_lock = threading.Lock()
    monitor_lock = threading.Lock()
    per_camera_stats = {cam_id: new_camera_stats() for cam_id in running_targets.keys()}
    monitor_samples = []
    worker_threads: List[threading.Thread] = []

    # Spawn concurrent workers per camera.
    for cam_id, info in running_targets.items():
        for _ in range(max(1, args.clients_per_camera)):
            t = threading.Thread(
                target=run_worker,
                args=(
                    stop_event,
                    client,
                    cam_id,
                    info["hls_url"],
                    per_camera_stats[cam_id],
                    stats_lock,
                    args.poll_interval_seconds,
                ),
                daemon=True,
            )
            worker_threads.append(t)
            t.start()

    # Monitor loop.
    try:
        while time.time() - started_at < duration_seconds:
            sample = {
                "ts": round(time.time(), 3),
                "uptime_seconds": int(time.time() - started_at),
            }
            result, err = safe_call(client.get_json, "/api/monitor/dataflow")
            if err:
                sample["monitor_error"] = err
            else:
                _, payload = result
                hw = payload.get("hardware", {})
                sample["cpu_percent"] = float(hw.get("cpu_percent", 0.0) or 0.0)
                sample["memory_percent"] = float(hw.get("memory_percent", 0.0) or 0.0)
                sample["memory_used_mb"] = float(hw.get("memory_used_mb", 0.0) or 0.0)

            with stats_lock:
                now = time.time()
                for cam_id, cstats in per_camera_stats.items():
                    last_ok = float(cstats.get("last_success_ts") or 0.0)
                    if last_ok > 0 and (now - last_ok) > 10.0:
                        cstats["stutter_events"] += 1
                        cstats["last_success_ts"] = now

            with monitor_lock:
                monitor_samples.append(sample)
            time.sleep(max(1.0, args.monitor_interval_seconds))
    finally:
        stop_event.set()
        for t in worker_threads:
            t.join(timeout=3.0)

        for cam_id in running_targets.keys():
            safe_call(client.post_json, f"/api/cameras/{cam_id}/stop", {"immediate": True})

    # Build report.
    finished_at = time.time()
    summary = {
        "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(),
        "finished_at": datetime.fromtimestamp(finished_at, tz=timezone.utc).isoformat(),
        "duration_seconds": int(finished_at - started_at),
        "preset": args.preset,
        "base_url": args.base_url,
        "clients_per_camera": args.clients_per_camera,
        "selected_cameras": sorted(running_targets.keys()),
        "camera_stats": {},
        "resource_summary": {},
    }

    with stats_lock:
        for cam_id, s in per_camera_stats.items():
            req_total = int(s["requests_total"])
            req_fail = int(s["requests_failed"])
            err_rate = (req_fail / req_total) if req_total else 0.0
            summary["camera_stats"][cam_id] = {
                "type": running_targets[cam_id]["type"],
                "requests_total": req_total,
                "requests_failed": req_fail,
                "error_rate": round(err_rate, 4),
                "playlist_ok": int(s["playlist_ok"]),
                "segment_ok": int(s["segment_ok"]),
                "stutter_events": int(s["stutter_events"]),
                "latency": summarize_latency(list(s["latency_ms_samples"])),
                "errors": dict(sorted(s["errors"].items())),
            }

    with monitor_lock:
        cpu_values = [x.get("cpu_percent", 0.0) for x in monitor_samples if "cpu_percent" in x]
        mem_values = [x.get("memory_percent", 0.0) for x in monitor_samples if "memory_percent" in x]
        mem_mb_values = [x.get("memory_used_mb", 0.0) for x in monitor_samples if "memory_used_mb" in x]
        summary["resource_summary"] = {
            "samples": len(monitor_samples),
            "cpu_max_percent": round(max(cpu_values), 2) if cpu_values else 0.0,
            "cpu_avg_percent": round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0.0,
            "memory_max_percent": round(max(mem_values), 2) if mem_values else 0.0,
            "memory_avg_percent": round(sum(mem_values) / len(mem_values), 2) if mem_values else 0.0,
            "memory_max_mb": round(max(mem_mb_values), 2) if mem_mb_values else 0.0,
        }

    report_file = args.report_file.strip()
    if not report_file:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.makedirs("config/soak_reports", exist_ok=True)
        report_file = f"config/soak_reports/stream_soak_{stamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("")
    print("Soak test finished.")
    print(f"Report: {report_file}")
    print(json.dumps(summary["resource_summary"], indent=2))
    for cam_id, csum in summary["camera_stats"].items():
        print(
            f"{cam_id}: error_rate={csum['error_rate']:.4f}, "
            f"stutter_events={csum['stutter_events']}, "
            f"p95={csum['latency']['p95_ms']}ms"
        )


if __name__ == "__main__":
    main()

