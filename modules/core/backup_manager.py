"""
Backup Manager

Creates and restores tamper-checked backups for config and log databases.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


class BackupManager:
    """Backup/restore workflow for project config data."""

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

    @staticmethod
    def _project_root(project_root: str | None = None) -> str:
        if project_root:
            return os.path.abspath(project_root)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @staticmethod
    def _backup_dir(project_root: str) -> str:
        path = os.path.join(project_root, "config", "backups")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def _candidate_paths(project_root: str) -> List[str]:
        rel_candidates = [
            "config/plc_connections.json",
            "config/plc_configs.json",
            "config/twincat_layout.json",
            "config/routing.json",
            "config/cameras.json",
            "config/camera_triggers.json",
            "config/alias_mappings.json",
            "config/system_logs.db",
            "config/automation_rules.db",
        ]
        return [os.path.join(project_root, rel_path) for rel_path in rel_candidates]

    @staticmethod
    def _sha256_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _cleanup_old_backups(backup_dir: str, keep_count: int) -> int:
        keep_count = max(1, int(keep_count))
        files = []
        for name in os.listdir(backup_dir):
            if not name.endswith(".tar.gz"):
                continue
            full = os.path.join(backup_dir, name)
            files.append((full, os.path.getmtime(full)))
        files.sort(key=lambda x: x[1], reverse=True)
        deleted = 0
        for full, _ in files[keep_count:]:
            try:
                os.remove(full)
                deleted += 1
            except Exception:
                pass
        return deleted

    @staticmethod
    def create_backup(project_root: str | None = None, keep_count: int = 30) -> Dict[str, Any]:
        root = BackupManager._project_root(project_root)
        backup_dir = BackupManager._backup_dir(root)
        timestamp = BackupManager._utc_now()
        backup_name = f"smarthome_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(backup_dir, backup_name)

        files_meta: List[Dict[str, Any]] = []
        files_to_pack: List[Tuple[str, str]] = []
        for source in BackupManager._candidate_paths(root):
            if not os.path.exists(source):
                continue
            rel = os.path.relpath(source, root).replace("\\", "/")
            files_to_pack.append((source, rel))
            files_meta.append(
                {
                    "path": rel,
                    "size": os.path.getsize(source),
                    "sha256": BackupManager._sha256_file(source),
                }
            )

        if not files_to_pack:
            raise RuntimeError("Keine Backup-Dateien gefunden")

        manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": 1,
            "project_root": os.path.basename(root),
            "files": files_meta,
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2).encode("utf-8")

        with tarfile.open(backup_path, "w:gz") as tar:
            for source, rel in files_to_pack:
                tar.add(source, arcname=rel, recursive=False)
            info = tarfile.TarInfo(name="BACKUP_MANIFEST.json")
            info.size = len(manifest_bytes)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(manifest_bytes))

        archive_sha = BackupManager._sha256_file(backup_path)
        deleted_old = BackupManager._cleanup_old_backups(backup_dir, keep_count=keep_count)
        return {
            "success": True,
            "backup_file": backup_name,
            "backup_path": backup_path,
            "sha256": archive_sha,
            "files_count": len(files_meta),
            "deleted_old_backups": deleted_old,
        }

    @staticmethod
    def list_backups(project_root: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        root = BackupManager._project_root(project_root)
        backup_dir = BackupManager._backup_dir(root)
        limit = max(1, min(int(limit), 500))
        entries = []
        for name in os.listdir(backup_dir):
            if not name.endswith(".tar.gz"):
                continue
            full = os.path.join(backup_dir, name)
            entries.append(
                {
                    "file": name,
                    "size": os.path.getsize(full),
                    "mtime": os.path.getmtime(full),
                    "sha256": BackupManager._sha256_file(full),
                }
            )
        entries.sort(key=lambda x: x["mtime"], reverse=True)
        return entries[:limit]

    @staticmethod
    def _extract_manifest(tar: tarfile.TarFile) -> Dict[str, Any]:
        member = tar.getmember("BACKUP_MANIFEST.json")
        with tar.extractfile(member) as f:
            return json.load(f)

    @staticmethod
    def verify_backup_file(backup_path: str) -> Dict[str, Any]:
        if not os.path.exists(backup_path):
            return {"ok": False, "error": "Backup-Datei nicht gefunden"}

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                manifest = BackupManager._extract_manifest(tar)
                file_entries = manifest.get("files", [])
                checked = 0
                for entry in file_entries:
                    rel = str(entry.get("path") or "")
                    expected = str(entry.get("sha256") or "")
                    member = tar.getmember(rel)
                    with tar.extractfile(member) as f:
                        digest = hashlib.sha256()
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            digest.update(chunk)
                        actual = digest.hexdigest()
                    checked += 1
                    if expected and actual != expected:
                        return {
                            "ok": False,
                            "checked": checked,
                            "broken_file": rel,
                            "error": "Checksum mismatch",
                        }

            return {"ok": True, "checked": checked, "broken_file": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def verify_backup(project_root: str | None, backup_file: str) -> Dict[str, Any]:
        root = BackupManager._project_root(project_root)
        backup_dir = BackupManager._backup_dir(root)
        backup_path = os.path.join(backup_dir, backup_file)
        result = BackupManager.verify_backup_file(backup_path)
        result["backup_file"] = backup_file
        return result

    @staticmethod
    def restore_backup(
        project_root: str | None,
        backup_file: str,
        dry_run: bool = False,
        create_pre_restore_backup: bool = True,
        keep_count: int = 30,
    ) -> Dict[str, Any]:
        root = BackupManager._project_root(project_root)
        backup_dir = BackupManager._backup_dir(root)
        backup_path = os.path.join(backup_dir, backup_file)

        verify = BackupManager.verify_backup_file(backup_path)
        if not verify.get("ok"):
            return {"success": False, "error": f"Integrity check failed: {verify.get('error')}"}

        pre_backup = None
        if create_pre_restore_backup and not dry_run:
            pre_backup = BackupManager.create_backup(root, keep_count=keep_count)

        restored = []
        with tarfile.open(backup_path, "r:gz") as tar:
            manifest = BackupManager._extract_manifest(tar)
            members = manifest.get("files", [])
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "restore_files": [str(m.get("path")) for m in members],
                    "pre_restore_backup": pre_backup,
                }

            with tempfile.TemporaryDirectory(prefix="smarthome_restore_") as tmp:
                tar.extractall(path=tmp)
                for entry in members:
                    rel = str(entry.get("path") or "")
                    if not rel:
                        continue
                    src = os.path.join(tmp, rel)
                    dst = os.path.join(root, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    restored.append(rel)

        return {
            "success": True,
            "dry_run": False,
            "restored_count": len(restored),
            "restored_files": restored,
            "pre_restore_backup": pre_backup,
        }
