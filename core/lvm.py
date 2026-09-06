"""
LVM Volume, Thin Pool, and Snapshot operations for Arvor Recovery Mode.
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Optional


class LVMManager:
    def __init__(self, simulate: bool = False, logger=None):
        self.simulate = simulate
        self.logger = logger or (lambda msg: None)

        # In-memory mock state for simulation mode (matching Discord mockup)
        self._sim_snapshots = [
            {"lv_name": "snap_root_2026_09_01", "vg_name": "arvor_vg", "origin": "root", "data_percent": "3.50", "lv_time": "2026-09-01 09:00:00"},
            {"lv_name": "snap_home_2026_09_01", "vg_name": "arvor_vg", "origin": "home", "data_percent": "0.95", "lv_time": "2026-09-01 09:00:00"},
            {"lv_name": "snap_var_2026_07_30", "vg_name": "arvor_vg", "origin": "var", "data_percent": "8.20", "lv_time": "2026-07-30 16:45:22"}
        ]
        self._sim_thin_pool = {
            "name": "arvor_thin_pool",
            "vg": "arvor_vg",
            "data_percent": "42.50",
            "metadata_percent": "18.30",
            "size": "450G"
        }

    def log(self, msg: str):
        self.logger(msg)

    def run_cmd(self, cmd: List[str]) -> str:
        self.log(f"$ {' '.join(cmd)}")
        if self.simulate:
            time.sleep(0.1)
            return ""
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] Command failed: {e.stderr.strip()}")
            raise

    def activate_vgs(self):
        """Activate all Volume Groups."""
        self.log("Activating all LVM Volume Groups...")
        if self.simulate:
            self.log("LVM: vgchange -ay executed [SIMULATED]")
            return
        self.run_cmd(["vgchange", "-ay"])
        self.run_cmd(["udevadm", "settle"])

    def list_vgs(self) -> List[Dict]:
        """Return list of volume groups."""
        if self.simulate:
            return [{"vg_name": "arvor_vg", "vg_size": "500.00g", "vg_free": "50.00g", "lv_count": "5"}]

        try:
            cmd = ["vgs", "--reportformat", "json", "-o", "vg_name,vg_size,vg_free,lv_count"]
            out = subprocess.check_output(cmd, text=True)
            data = json.loads(out)
            report = data.get("report", [])
            if report and "vg" in report[0]:
                return report[0]["vg"]
            return []
        except Exception as e:
            self.log(f"[WARN] Failed to list VGs: {e}")
            return []

    def get_thin_pool_info(self, vg_name: str = "arvor_vg") -> Optional[Dict]:
        """Get Thin Pool status including data and metadata occupancy."""
        if self.simulate:
            return self._sim_thin_pool

        try:
            cmd = ["lvs", "--reportformat", "json", "-o", "lv_name,vg_name,lv_attr,data_percent,metadata_percent,lv_size", vg_name]
            out = subprocess.check_output(cmd, text=True)
            data = json.loads(out)
            for lv in data.get("report", [])[0].get("lv", []):
                attr = lv.get("lv_attr", "")
                if attr.startswith("t") or "thin" in lv.get("lv_name", ""):
                    return {
                        "name": lv.get("lv_name"),
                        "vg": vg_name,
                        "data_percent": lv.get("data_percent", "0.00"),
                        "metadata_percent": lv.get("metadata_percent", "0.00"),
                        "size": lv.get("lv_size", "unknown")
                    }
            return None
        except Exception as e:
            self.log(f"[WARN] Failed to inspect thin pool: {e}")
            return None

    def list_snapshots(self, vg_name: Optional[str] = None) -> List[Dict]:
        """List all snapshots in the specified volume group or across all VGs."""
        if self.simulate:
            if vg_name:
                return [s for s in self._sim_snapshots if s["vg_name"] == vg_name]
            return list(self._sim_snapshots)

        cmd = ["lvs", "--reportformat", "json", "-o", "lv_name,vg_name,origin,data_percent,lv_time,lv_attr,lv_tags"]
        if vg_name:
            cmd.append(vg_name)

        try:
            out = subprocess.check_output(cmd, text=True)
            data = json.loads(out)
            snapshots = []
            for lv in data.get("report", [])[0].get("lv", []):
                origin = lv.get("origin", "").strip()
                name = lv.get("lv_name", "").strip()
                if not origin:
                    continue  # Not a snapshot

                snapshots.append({
                    "lv_name": name,
                    "vg_name": lv.get("vg_name", ""),
                    "origin": origin,
                    "data_percent": lv.get("data_percent", "0.00"),
                    "lv_time": lv.get("lv_time", "")
                })
            return snapshots
        except Exception as e:
            self.log(f"[WARN] Failed to list snapshots: {e}")
            return []

    def merge_snapshot(self, vg_name: str, snapshot_name: str) -> bool:
        """Rollback: Merge a snapshot into its origin volume."""
        target = f"/dev/{vg_name}/{snapshot_name}"
        self.log(f"Preparing to merge snapshot {target}...")

        if self.simulate:
            self.log(f"Running: lvconvert --merge {target} [SIMULATED]")
            time.sleep(0.3)
            self._sim_snapshots = [s for s in self._sim_snapshots if not (s["vg_name"] == vg_name and s["lv_name"] == snapshot_name)]
            self.log(f"Snapshot {target} successfully merged.")
            return True

        try:
            self.run_cmd(["lvconvert", "--merge", target])
            self.log(f"Rollback to {target} executed successfully.")
            return True
        except Exception as e:
            self.log(f"[ERROR] Failed to merge snapshot {target}: {e}")
            return False

    def delete_snapshot(self, vg_name: str, snapshot_name: str) -> bool:
        """Permanently delete a snapshot to free space."""
        target = f"/dev/{vg_name}/{snapshot_name}"
        self.log(f"Deleting snapshot {target}...")

        if self.simulate:
            self.log(f"taking origin dependencies for {target}...")
            time.sleep(0.15)
            self.log(f"taking logical volume {target}...")
            time.sleep(0.15)
            self.log(f"1 metadata from Volume Group {vg_name} removed.")
            self.log(f"snapshot {target} removed.")
            self._sim_snapshots = [s for s in self._sim_snapshots if not (s["vg_name"] == vg_name and s["lv_name"] == snapshot_name)]
            return True

        try:
            self.run_cmd(["lvremove", "-f", target])
            self.log(f"Snapshot {target} deleted successfully.")
            return True
        except Exception as e:
            self.log(f"[ERROR] Failed to delete snapshot {target}: {e}")
            return False

    def create_snapshot(self, vg_name: str, origin_lv: str = "root", name: Optional[str] = None) -> bool:
        """Create a new manual thin snapshot."""
        if not name:
            name = f"manual_{time.strftime('%Y%m%d_%H%M%S')}"

        origin_path = f"/dev/{vg_name}/{origin_lv}"
        self.log(f"Creating snapshot '{name}' from {origin_path}...")

        if self.simulate:
            time.sleep(0.2)
            self._sim_snapshots.insert(0, {
                "lv_name": name,
                "vg_name": vg_name,
                "origin": origin_lv,
                "data_percent": "0.01",
                "lv_time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            self.log(f"Snapshot '{name}' created successfully. [SIMULATED]")
            return True

        try:
            self.run_cmd(["lvcreate", "-s", "--name", name, "-k", "n", origin_path])
            self.log(f"Snapshot '{name}' created successfully.")
            return True
        except Exception as e:
            self.log(f"[ERROR] Failed to create snapshot {name}: {e}")
            return False
