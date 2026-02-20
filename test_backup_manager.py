import os
import json
from pathlib import Path

from modules.core.backup_manager import BackupManager


def _write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_backup_create_verify_list_restore_dry_run(tmp_path):
    root = tmp_path / "project"
    config = root / "config"

    _write(config / "plc_connections.json", b'{"active":"plc_001"}')
    _write(config / "routing.json", b'{"routes":[]}')
    _write(config / "system_logs.db", b"sqlite-mock")

    created = BackupManager.create_backup(project_root=str(root), keep_count=5)
    assert created["success"] is True
    assert created["files_count"] >= 3

    backup_file = created["backup_file"]

    listed = BackupManager.list_backups(project_root=str(root), limit=10)
    assert any(entry["file"] == backup_file for entry in listed)

    verify = BackupManager.verify_backup(project_root=str(root), backup_file=backup_file)
    assert verify["ok"] is True
    assert verify["checked"] >= 3

    dry = BackupManager.restore_backup(
        project_root=str(root),
        backup_file=backup_file,
        dry_run=True,
        create_pre_restore_backup=False,
    )
    assert dry["success"] is True
    assert dry["dry_run"] is True
    assert "config/plc_connections.json" in dry["restore_files"]
