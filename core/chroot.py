"""
Rescue Chroot Environment Manager for Arvor Recovery Mode.
"""

import os
import shutil
import subprocess
import time
from typing import Dict, List, Optional


class ChrootManager:
    def __init__(self, simulate: bool = False, logger=None):
        self.simulate = simulate
        self.logger = logger or (lambda msg: None)
        self.mount_dir = "/mnt/arvor_rescue"

    def log(self, msg: str):
        self.logger(msg)

    def prepare_and_enter(self, root_dev: str, boot_dev: Optional[str] = None, efi_dev: Optional[str] = None) -> bool:
        """Mounts the root volume, binds kernel filesystems, and launches a bash rescue shell."""
        self.log(f"Preparing rescue chroot on {root_dev}...")

        if self.simulate:
            self.log(f"mkdir -p {self.mount_dir}")
            self.log(f"mount {root_dev} {self.mount_dir}")
            self.log("# /dev, /proc, /sys, and /run...")
            self.log("chroot environment ready.")
            self.log("[SIMULATED] Spawning rescue shell `/bin/bash` in chroot...")
            time.sleep(1.0)
            self.log("[SIMULATED] Rescue shell exited cleanly. Unmounting subsystems...")
            self.log("Clean unmount complete.")
            return True

        os.makedirs(self.mount_dir, exist_ok=True)

        try:
            # Mount root volume
            self.log(f"Mounting {root_dev} to {self.mount_dir}...")
            subprocess.run(["mount", root_dev, self.mount_dir], check=True)

            # Optional /boot and /boot/efi
            if boot_dev:
                boot_mnt = os.path.join(self.mount_dir, "boot")
                os.makedirs(boot_mnt, exist_ok=True)
                self.log(f"Mounting {boot_dev} to {boot_mnt}...")
                subprocess.run(["mount", boot_dev, boot_mnt], check=False)

            if efi_dev:
                efi_mnt = os.path.join(self.mount_dir, "boot", "efi")
                os.makedirs(efi_mnt, exist_ok=True)
                self.log(f"Mounting {efi_dev} to {efi_mnt}...")
                subprocess.run(["mount", efi_dev, efi_mnt], check=False)

            # Bind system mounts
            bind_mounts = ["/dev", "/dev/pts", "/proc", "/sys", "/run"]
            for bm in bind_mounts:
                target_bm = os.path.join(self.mount_dir, bm.lstrip("/"))
                os.makedirs(target_bm, exist_ok=True)
                self.log(f"Binding {bm} -> {target_bm}")
                subprocess.run(["mount", "--bind", bm, target_bm], check=True)

            # DNS setup
            resolv_path = os.path.join(self.mount_dir, "etc", "resolv.conf")
            if os.path.exists("/etc/resolv.conf"):
                try:
                    shutil.copy2("/etc/resolv.conf", resolv_path)
                except Exception:
                    pass

            self.log("Rescue environment mounted. Launching interactive chroot shell...")
            # Run bash interactively
            subprocess.run(["chroot", self.mount_dir, "/bin/bash"])
            self.log("User exited chroot shell.")
            return True

        except Exception as e:
            self.log(f"[ERROR] Failed during chroot lifecycle: {e}")
            return False

        finally:
            self.cleanup()

    def cleanup(self):
        """Clean unmount in reverse order."""
        if self.simulate:
            return

        self.log(f"Unmounting chroot subsystems from {self.mount_dir}...")
        for m in ["/boot/efi", "/boot", "/run", "/sys", "/proc", "/dev/pts", "/dev"]:
            target = os.path.join(self.mount_dir, m.lstrip("/"))
            try:
                subprocess.run(["umount", "-l", target], stderr=subprocess.DEVNULL)
            except Exception:
                pass

        try:
            subprocess.run(["umount", "-l", self.mount_dir], stderr=subprocess.DEVNULL)
        except Exception:
            pass
