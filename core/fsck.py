"""
Filesystem check & repair utilities (fsck / xfs_repair) for Arvor Recovery Mode.
"""

import subprocess
import time
from typing import Dict, List, Optional


class FsckManager:
    def __init__(self, simulate: bool = False, logger=None):
        self.simulate = simulate
        self.logger = logger or (lambda msg: None)

    def log(self, msg: str):
        self.logger(msg)

    def detect_fstype(self, dev_path: str) -> str:
        """Detect filesystem type using blkid."""
        if self.simulate:
            if "root" in dev_path or "vg" in dev_path:
                return "xfs"
            return "ext4"

        try:
            cmd = ["blkid", "-s", "TYPE", "-o", "value", dev_path]
            out = subprocess.check_output(cmd, text=True).strip()
            return out
        except Exception:
            return "unknown"

    def check_volume(self, dev_path: str, repair: bool = False) -> Dict:
        """Run non-destructive check (or repair) on a given volume device."""
        fstype = self.detect_fstype(dev_path)
        self.log(f"Initiating volume check on {dev_path} (Detected FS: {fstype})...")

        if self.simulate:
            self.log(f"[SIMULATED] Inspecting superblock on {dev_path}...")
            time.sleep(0.3)
            self.log(f"[SIMULATED] Checking inode allocation and directory structures...")
            time.sleep(0.4)
            self.log(f"[SIMULATED] Verifying block group descriptors and journal...")
            time.sleep(0.3)
            self.log(f"[SIMULATED] Volume {dev_path}: Clean. 0 errors found.")
            return {"success": True, "dev": dev_path, "fstype": fstype, "status": "clean", "output": "Clean"}

        if fstype == "xfs":
            cmd = ["xfs_repair"]
            if not repair:
                cmd.append("-n")  # No modify mode
            cmd.append(dev_path)
        elif fstype in ("ext4", "ext3", "ext2"):
            cmd = ["e2fsck", "-f"]
            if not repair:
                cmd.append("-n")
            else:
                cmd.append("-p")
            cmd.append(dev_path)
        else:
            cmd = ["fsck", "-N" if not repair else "-a", dev_path]

        self.log(f"Executing: {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output_lines = []
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    self.log(f"fsck: {line_str}")
                    output_lines.append(line_str)
            proc.wait()

            success = proc.returncode in (0, 1)  # 0 = clean, 1 = errors corrected
            return {
                "success": success,
                "dev": dev_path,
                "fstype": fstype,
                "status": "clean" if proc.returncode == 0 else "repaired" if proc.returncode == 1 else "error",
                "returncode": proc.returncode,
                "output": "\n".join(output_lines)
            }
        except Exception as e:
            self.log(f"[ERROR] fsck execution failed: {e}")
            return {"success": False, "dev": dev_path, "fstype": fstype, "status": "failed", "error": str(e)}
