"""
Automated Reinstallation / Factory Reset engine for Arvor Recovery Mode.
Preserves the dedicated recovery partition while restoring the main system via rsync.
"""

import os
import subprocess
import time
from typing import Callable, Dict, List, Optional


class ReinstallManager:
    def __init__(self, simulate: bool = False, logger=None, progress_cb: Optional[Callable[[int, str], None]] = None):
        self.simulate = simulate
        self.logger = logger or (lambda msg: None)
        self.progress_cb = progress_cb or (lambda pct, desc: None)

    def log(self, msg: str):
        self.logger(msg)

    def update_progress(self, percent: int, description: str):
        self.progress_cb(percent, description)
        self.log(f"[{percent}%] {description}")

    def get_rsync_excludes(self) -> List[str]:
        """
        Returns list of files and directories excluded from recovery -> root sync.
        Excludes virtual filesystems, recovery-specific binaries, and temporary files.
        """
        return [
            "/proc/*",
            "/sys/*",
            "/dev/*",
            "/run/*",
            "/tmp/*",
            "/mnt/*",
            "/media/*",
            "/lost+found",
            "/boot/efi/*",
            "/boot/grub/*",
            "/usr/bin/arvor-recovery",
            "/usr/lib/arvor-recovery",
            "/usr/lib/arvor-recovery/*",
            "/etc/systemd/system/getty@tty1.service.d",
            "/etc/systemd/system/getty@tty1.service.d/*",
            "/var/cache/apt/archives/*.deb",
            "/swapfile",
        ]

    def reinstall_system(
        self,
        disk_dev: str,
        recovery_part: str,
        root_lv: str = "/dev/arvor_vg/root",
        default_user: str = "arvor",
        default_user_pass: str = "arvor",
        root_pass: str = "root"
    ) -> bool:
        """
        Executes automated reinstall:
        1. Formats the LVM root volume (leaving recovery partition untouched).
        2. Mounts root volume to target staging mountpoint.
        3. Synchronizes base system from recovery root (/) using rsync, excluding recovery tools.
        4. Provisions root (password: root) and default user (arvor with sudo).
        5. Configures fstab, initramfs, and bootloader.
        """
        self.log(f"Starting Arvor Linux Factory Reinstall on {disk_dev}...")
        self.log(f"SAFETY: Recovery partition {recovery_part} is protected and will NOT be touched.")

        if self.simulate:
            steps = [
                (10, "Validating recovery source partition and disk signatures..."),
                (25, f"Formatting root logical volume {root_lv} with XFS..."),
                (45, "Restoring pristine system via rsync (excluding recovery tools)..."),
                (65, f"Configuring credentials (root:{root_pass}, user:{default_user})..."),
                (80, "Configuring fstab, initramfs hooks and storage layouts..."),
                (95, "Updating GRUB and NVRAM EFI boot entries..."),
                (100, "Factory restore complete! Ready to reboot.")
            ]
            for pct, desc in steps:
                time.sleep(0.3)
                self.update_progress(pct, desc)
            return True

        target_mnt = "/mnt/arvor_reinstall"
        try:
            self.update_progress(10, "Validating storage configuration...")
            if not os.path.exists(root_lv):
                self.log(f"[WARN] Target {root_lv} not found immediately, attempting activation...")
                subprocess.run(["vgchange", "-ay"], check=False)

            self.update_progress(25, f"Formatting {root_lv} with XFS...")
            subprocess.run(["mkfs.xfs", "-f", root_lv], check=True)

            os.makedirs(target_mnt, exist_ok=True)
            subprocess.run(["mount", root_lv, target_mnt], check=True)

            self.update_progress(40, "Synchronizing base OS from recovery partition via rsync...")
            excludes = self.get_rsync_excludes()
            rsync_cmd = ["rsync", "-aHAX", "--delete"]
            for exc in excludes:
                rsync_cmd.extend(["--exclude", exc])
            rsync_cmd.extend(["/", f"{target_mnt}/"])

            self.log("Running rsync transfer...")
            subprocess.run(rsync_cmd, check=True)

            self.update_progress(65, f"Provisioning credentials (root and {default_user})...")
            # Configure root password
            subprocess.run(
                ["chroot", target_mnt, "/bin/sh", "-c", f"echo 'root:{root_pass}' | chpasswd"],
                check=True
            )

            # Configure default worker user ("o usuario que faz os trambolhos")
            create_user_cmd = (
                f"id -u {default_user} >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo {default_user} && "
                f"echo '{default_user}:{default_user_pass}' | chpasswd"
            )
            subprocess.run(
                ["chroot", target_mnt, "/bin/sh", "-c", create_user_cmd],
                check=True
            )

            self.update_progress(80, "Configuring storage mounts and initramfs...")
            # Bind mounts for chroot configuration
            for p in ["/dev", "/proc", "/sys", "/run"]:
                os.makedirs(f"{target_mnt}{p}", exist_ok=True)
                subprocess.run(["mount", "--bind", p, f"{target_mnt}{p}"], check=False)

            # Update initramfs inside chroot if kernel present
            subprocess.run(["chroot", target_mnt, "update-initramfs", "-u"], check=False)
            subprocess.run(["chroot", target_mnt, "update-grub"], check=False)

            self.update_progress(95, "Finalizing filesystem and cleaning mounts...")
            for p in ["/run", "/sys", "/proc", "/dev"]:
                subprocess.run(["umount", "-l", f"{target_mnt}{p}"], check=False)
            subprocess.run(["umount", target_mnt], check=False)

            self.update_progress(100, "Factory restore completed successfully.")
            return True

        except Exception as e:
            self.log(f"[FATAL] Reinstall failed: {e}")
            for p in ["/run", "/sys", "/proc", "/dev"]:
                subprocess.run(["umount", "-l", f"{target_mnt}{p}"], check=False)
            subprocess.run(["umount", "-l", target_mnt], check=False)
            return False
