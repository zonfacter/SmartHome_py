"""
Camera Diagnostics Module
Automatische Erkennung von Kamera-Faehigkeiten: Ports, Streams, ONVIF, PTZ, Snapshots.
"""

import socket
import struct
import subprocess
import json
import logging
import uuid
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Gaengige Kamera-Ports
DEFAULT_PORTS = [80, 443, 554, 8080, 8000, 8443, 8899, 8999]

# RTSP-URL-Patterns (gaengige Hersteller)
RTSP_PATTERNS = {
    'mainstream': [
        '/1/h264major',
        '/live/ch0',
        '/Streaming/Channels/101',
        '/cam/realmonitor?channel=1&subtype=0',
    ],
    'substream': [
        '/1/h264minor',
        '/live/ch1',
        '/Streaming/Channels/102',
        '/cam/realmonitor?channel=1&subtype=1',
    ],
}

# Gaengige ONVIF-Ports
ONVIF_PORTS = [80, 8080, 8999]

# Gaengige Snapshot-URLs
SNAPSHOT_URLS = [
    '/jpgimage/1/image.jpg',
    '/snapshot.jpg',
    '/cgi-bin/snapshot.cgi',
    '/ISAPI/Streaming/channels/101/picture',
]


def _scan_port(host, port, timeout=2.0):
    """Prueft ob ein TCP-Port offen ist."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return port if result == 0 else None
    except Exception:
        return None


def _probe_rtsp_stream(host, path, port=554, timeout=5):
    """Prueft einen RTSP-Stream via ffprobe und gibt Stream-Info zurueck."""
    url = f"rtsp://{host}:{port}{path}"
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-rtsp_transport', 'tcp',
                url
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        if not streams:
            return None

        video = next((s for s in streams if s.get('codec_type') == 'video'), None)
        if not video:
            return None

        # Framerate parsen (z.B. "30/1" -> 30)
        fps = None
        r_frame_rate = video.get('r_frame_rate', '')
        if '/' in r_frame_rate:
            num, den = r_frame_rate.split('/')
            try:
                fps = round(int(num) / int(den))
            except (ValueError, ZeroDivisionError):
                pass

        return {
            'url': url,
            'path': path,
            'codec': video.get('codec_name', 'unknown'),
            'width': video.get('width'),
            'height': video.get('height'),
            'fps': fps,
            'profile': video.get('profile', ''),
        }
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        logger.debug(f"RTSP probe failed for {url}: {e}")
        return None


def _check_onvif(host, port, user='admin', password='admin'):
    """Versucht ONVIF-Verbindung und sammelt Infos."""
    try:
        from onvif import ONVIFCamera
        cam = ONVIFCamera(host, port, user, password)

        result = {
            'available': True,
            'port': port,
        }

        # Device Info
        try:
            device_service = cam.create_devicemgmt_service()
            info = device_service.GetDeviceInformation()
            result['device_info'] = {
                'manufacturer': getattr(info, 'Manufacturer', ''),
                'model': getattr(info, 'Model', ''),
                'firmware': getattr(info, 'FirmwareVersion', ''),
                'serial': getattr(info, 'SerialNumber', ''),
            }
        except Exception as e:
            logger.debug(f"ONVIF GetDeviceInformation failed: {e}")

        # Media Profiles
        try:
            media_service = cam.create_media_service()
            profiles = media_service.GetProfiles()
            result['profiles'] = []
            for p in profiles:
                profile_info = {
                    'name': getattr(p, 'Name', ''),
                    'token': getattr(p, 'token', ''),
                }
                # Stream URI
                try:
                    stream_setup = {
                        'Stream': 'RTP-Unicast',
                        'Transport': {'Protocol': 'RTSP'}
                    }
                    uri_resp = media_service.GetStreamUri({
                        'StreamSetup': stream_setup,
                        'ProfileToken': p.token
                    })
                    profile_info['stream_uri'] = getattr(uri_resp, 'Uri', '')
                except Exception:
                    pass

                # Video-Encoder Resolution
                if hasattr(p, 'VideoEncoderConfiguration') and p.VideoEncoderConfiguration:
                    vec = p.VideoEncoderConfiguration
                    if hasattr(vec, 'Resolution') and vec.Resolution:
                        profile_info['resolution'] = f"{vec.Resolution.Width}x{vec.Resolution.Height}"

                # PTZ check
                profile_info['has_ptz'] = hasattr(p, 'PTZConfiguration') and p.PTZConfiguration is not None

                result['profiles'].append(profile_info)

            # Snapshot URI (erstes Profil)
            if profiles:
                try:
                    snap = media_service.GetSnapshotUri({'ProfileToken': profiles[0].token})
                    result['snapshot_uri'] = getattr(snap, 'Uri', '')
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"ONVIF Media service failed: {e}")

        # PTZ Service
        try:
            ptz_service = cam.create_ptz_service()
            if ptz_service:
                result['ptz_available'] = True
                try:
                    nodes = ptz_service.GetNodes()
                    result['ptz_nodes'] = len(nodes) if nodes else 0
                except Exception:
                    pass
        except Exception:
            result['ptz_available'] = False

        return result
    except Exception as e:
        logger.debug(f"ONVIF check failed on port {port}: {e}")
        return None


def _check_snapshot(host, path, user='admin', password='admin', timeout=3):
    """Prueft ob eine Snapshot-URL erreichbar ist."""
    try:
        import urllib.request
        url = f"http://{host}{path}"

        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, user, password)
        auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(auth_handler)

        req = urllib.request.Request(url, method='HEAD')
        resp = opener.open(req, timeout=timeout)
        content_type = resp.headers.get('Content-Type', '')

        if 'image' in content_type or resp.status == 200:
            return {
                'url': url,
                'path': path,
                'content_type': content_type,
                'status': resp.status,
            }
        return None
    except Exception:
        return None


def diagnose_camera(host, user='admin', password='admin'):
    """
    Fuehrt eine vollstaendige Diagnose einer Kamera durch.

    Args:
        host: IP-Adresse der Kamera
        user: ONVIF/HTTP Benutzername
        password: ONVIF/HTTP Passwort

    Returns:
        dict mit allen Diagnose-Ergebnissen
    """
    result = {
        'host': host,
        'ports': [],
        'streams': [],
        'onvif': None,
        'snapshot': None,
    }

    with ThreadPoolExecutor(max_workers=12) as executor:
        # 1. Port-Scan (parallel)
        port_futures = {
            executor.submit(_scan_port, host, port): port
            for port in DEFAULT_PORTS
        }
        for future in as_completed(port_futures, timeout=5):
            try:
                open_port = future.result()
                if open_port is not None:
                    result['ports'].append(open_port)
            except Exception:
                pass
        result['ports'].sort()

        # 2. RTSP-Probe (nur wenn Port 554 offen)
        if 554 in result['ports']:
            stream_futures = []
            for stream_type, patterns in RTSP_PATTERNS.items():
                for path in patterns:
                    f = executor.submit(_probe_rtsp_stream, host, path)
                    stream_futures.append((f, stream_type))

            for future, stream_type in stream_futures:
                try:
                    info = future.result(timeout=8)
                    if info:
                        info['stream_type'] = stream_type
                        result['streams'].append(info)
                except Exception:
                    pass

        # 3. ONVIF Discovery (auf offenen Ports)
        onvif_ports_to_try = [p for p in ONVIF_PORTS if p in result['ports']]
        for port in onvif_ports_to_try:
            try:
                onvif_result = _check_onvif(host, port, user, password)
                if onvif_result and onvif_result.get('available'):
                    result['onvif'] = onvif_result
                    break
            except Exception:
                pass

        # 4. Snapshot-Test (nur wenn Port 80 offen)
        if 80 in result['ports']:
            for path in SNAPSHOT_URLS:
                try:
                    snap = _check_snapshot(host, path, user, password)
                    if snap:
                        result['snapshot'] = snap
                        break
                except Exception:
                    pass

    return result


# ========================================================================
# NETZWERK-SCAN
# ========================================================================

# Kamera-typische Ports fuer schnellen Scan
CAMERA_SCAN_PORTS = [554, 8999, 8080, 80]

# WS-Discovery Multicast Adresse/Port (ONVIF Standard)
WS_DISCOVERY_MULTICAST = ('239.255.255.250', 3702)

# WS-Discovery SOAP Probe Template
WS_DISCOVERY_PROBE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{msg_id}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>"""


def _get_local_subnet():
    """Ermittelt das lokale Subnetz (z.B. '192.168.2') aus den Netzwerk-Interfaces."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split('.')
        if len(parts) == 4:
            return '.'.join(parts[:3]), local_ip
    except Exception:
        pass
    return None, None


def _ws_discovery_probe(timeout=4):
    """
    Sendet WS-Discovery Multicast Probe und sammelt Antworten.
    Gibt Liste von gefundenen Hosts (IPs) zurueck.
    """
    found_hosts = set()
    msg = WS_DISCOVERY_PROBE.format(msg_id=uuid.uuid4())

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        sock.sendto(msg.encode('utf-8'), WS_DISCOVERY_MULTICAST)

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                data, addr = sock.recvfrom(65535)
                host_ip = addr[0]
                found_hosts.add(host_ip)
                logger.debug(f"WS-Discovery: Antwort von {host_ip}")
            except socket.timeout:
                break
            except Exception:
                continue

        sock.close()
    except Exception as e:
        logger.debug(f"WS-Discovery Fehler: {e}")

    return list(found_hosts)


def _scan_host_camera_ports(host, timeout=1.0, ports=None):
    """Prueft ob ein Host kamera-typische Ports offen hat."""
    open_ports = []
    for port in (ports or CAMERA_SCAN_PORTS):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                open_ports.append(port)
        except Exception:
            pass
    return open_ports if open_ports else None


def _quick_identify(host, open_ports):
    """Schnelle Identifikation eines Hosts anhand offener Ports."""
    info = {
        'host': host,
        'ports': open_ports,
        'type': 'unknown',
        'name': '',
    }

    has_rtsp = 554 in open_ports
    has_onvif_likely = 8999 in open_ports or 8080 in open_ports
    has_http = 80 in open_ports

    if has_rtsp:
        info['type'] = 'camera'
    elif has_onvif_likely:
        info['type'] = 'camera'
    elif has_http:
        info['type'] = 'possible'

    try:
        hostname = socket.getfqdn(host)
        if hostname and hostname != host:
            info['name'] = hostname
    except Exception:
        pass

    return info


def scan_network(subnet=None, scan_range=None, ports=None, user='admin', password='admin'):
    """
    Scannt das lokale Netzwerk nach Kameras.

    Strategie:
    1. WS-Discovery Multicast Probe (findet ONVIF-Kameras sofort)
    2. Parallel Port-Scan auf Subnet fuer konfigurierte Ports

    Args:
        subnet: Subnet-Prefix (z.B. '192.168.2'). Wenn None, wird automatisch ermittelt.
        scan_range: Tuple (start, end) fuer IP-Range. Default: (1, 254)
        ports: Liste der zu scannenden Ports. Default: CAMERA_SCAN_PORTS
        user: Benutzername fuer ONVIF/HTTP
        password: Passwort fuer ONVIF/HTTP

    Returns:
        dict mit Scan-Ergebnissen
    """
    if scan_range is None:
        scan_range = (1, 254)

    scan_ports = ports if ports else CAMERA_SCAN_PORTS

    result = {
        'devices': [],
        'scan_method': [],
        'subnet': subnet,
        'local_ip': None,
        'ports_scanned': scan_ports,
    }

    if not subnet:
        subnet, local_ip = _get_local_subnet()
        result['local_ip'] = local_ip
        if not subnet:
            result['error'] = 'Konnte lokales Subnetz nicht ermitteln'
            return result
    result['subnet'] = subnet

    found_hosts = {}

    # 1. WS-Discovery (schnell, ~3s)
    logger.info("Netzwerk-Scan: Starte WS-Discovery Probe...")
    result['scan_method'].append('ws-discovery')
    try:
        ws_hosts = _ws_discovery_probe(timeout=3)
        for host in ws_hosts:
            if host.startswith(subnet + '.'):
                found_hosts[host] = {
                    'host': host,
                    'ports': [],
                    'type': 'camera',
                    'name': '',
                    'discovery': 'onvif',
                }
        logger.info(f"WS-Discovery: {len(ws_hosts)} Geraete gefunden")
    except Exception as e:
        logger.debug(f"WS-Discovery fehlgeschlagen: {e}")

    # 2. Port-Scan (parallel, 64 Threads, ~0.8s Timeout pro Host)
    logger.info(f"Netzwerk-Scan: Port-Scan auf {subnet}.{scan_range[0]}-{scan_range[1]}...")
    result['scan_method'].append('port-scan')

    hosts_to_scan = [
        f"{subnet}.{i}" for i in range(scan_range[0], scan_range[1] + 1)
    ]
    if result.get('local_ip'):
        hosts_to_scan = [h for h in hosts_to_scan if h != result['local_ip']]

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {
            executor.submit(_scan_host_camera_ports, host, 0.8, scan_ports): host
            for host in hosts_to_scan
        }
        for future in as_completed(futures, timeout=30):
            host = futures[future]
            try:
                open_ports = future.result()
                if open_ports:
                    if host in found_hosts:
                        found_hosts[host]['ports'] = open_ports
                    else:
                        info = _quick_identify(host, open_ports)
                        found_hosts[host] = info
            except Exception:
                pass

    for host, info in sorted(found_hosts.items(), key=lambda x: x[0]):
        if info.get('type') in ('camera', 'possible'):
            if 'discovery' not in info:
                info['discovery'] = 'port-scan'
            result['devices'].append(info)

    logger.info(f"Netzwerk-Scan abgeschlossen: {len(result['devices'])} Geraete gefunden")
    return result
