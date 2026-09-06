"""
Disk & Partition detection and management for Arvor Recovery Mode.
"""

import json
import os
import subprocess
from typing import Dict, List, Optional


class DiskManager:
    def __init__(self, simulate: bool = False, logger=None):
        self.simulate = simulate
        self.logger = logger or (lambda msg: None)

    def log(self, msg: str):
        self.logger(msg)

    def run_cmd(self, cmd: List[str]) -> str:
        self.log(f"$ {' '.join(cmd)}")
        if self.simulate:
            return ""
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] Command failed: {e.stderr.strip()}")
            raise

    def list_block_devices(self) -> List[Dict]:
        """List all physical and virtual block devices using lsblk JSON output."""
        if self.simulate:
            return [
                {
                    "name": "nvme0n1",
                    "size": "512G",
                    "type": "disk",
                    "model": "Samsung SSD 980 500GB",
                    "children": [
                        {"name": "nvme0n1p1", "size": "512M", "type": "part", "fstype": "vfat", "mountpoint": "/boot/efi", "label": "ESP"},
                        {"name": "nvme0n1p2", "size": "1G", "type": "part", "fstype": "ext4", "mountpoint": "/boot", "label": "BOOT"},
                        {"name": "nvme0n1p3", "size": "4G", "type": "part", "fstype": "ext4", "mountpoint": "/recovery", "label": "ARVOR_RECOVERY"},
                        {"name": "nvme0n1p4", "size": "506.5G", "type": "part", "fstype": "LVM2_member", "label": "LVM"},
                    ]
                }
            ]

        try:
            cmd = ["lsblk", "-J", "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL,MODEL"]
            out = subprocess.check_output(cmd, text=True)
            data = json.loads(out)
            return data.get("blockdevices", [])
        except Exception as e:
            self.log(f"[WARN] lsblk JSON failed ({e}), falling back to empty list")
            return []

    def find_recovery_partition(self) -> Optional[Dict]:
        """Find the dedicated recovery partition by label or mountpoint."""
        devices = self.list_block_devices()
        for dev in devices:
            for child in dev.get("children", []):
                label = (child.get("label") or "").upper()
                mountpoint = child.get("mountpoint") or ""
                if "RECOVERY" in label or "/recovery" in mountpoint:
                    return child
        return None

    def find_esp_partition(self) -> Optional[Dict]:
        """Find the EFI System Partition (ESP)."""
        devices = self.list_block_devices()
        for dev in devices:
            for child in dev.get("children", []):
                label = (child.get("label") or "").upper()
                mount = child.get("mountpoint") or ""
                fstype = child.get("fstype") or ""
                if "ESP" in label or "/boot/efi" in mount or (fstype == "vfat" and "p1" in child.get("name", "")):
                    return child
        return None

    def get_root_lvm_partition(self) -> Optional[str]:
        """Locate which partition hosts the LVM Physical Volume for Arvor."""
        devices = self.list_block_devices()
        for dev in devices:
            for child in dev.get("children", []):
                fstype = child.get("fstype") or ""
                if "lvm" in fstype.lower():
                    return child.get("path") or f"/dev/{child.get('name')}"
        return None
