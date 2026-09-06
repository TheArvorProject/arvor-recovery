"""
System Information & Hardware Diagnostics for Arvor Recovery Mode.
"""

import os
import platform
import subprocess
from typing import Dict, Optional


class SysInfoCollector:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.build_version = "Build 2026.09.1-rev0-x86_64"

    def get_system_summary(self) -> Dict:
        if self.simulate:
            return {
                "os_name": "Arvor Linux Recovery Mode",
                "build": self.build_version,
                "kernel": "6.12.86+deb13-amd64",
                "cpu": "AMD Ryzen 7 5800X (16 cores)",
                "memory_total": "16384 MB",
                "memory_used": "1420 MB (8.6%)",
                "vg_name": "arvor_vg",
                "thin_pool": "arvor_thin_pool (Data: 42.5%, Meta: 18.3%)",
                "efi_mode": "UEFI x86_64 (NVRAM Accessible)",
                "recovery_part": "/dev/nvme0n1p3 (4.0 GB, ext4)"
            }

        # Memory info
        mem_total, mem_avail = 0, 0
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        mem_avail = int(line.split()[1]) // 1024
        except Exception:
            pass
        mem_used = mem_total - mem_avail
        mem_pct = (mem_used / mem_total * 100) if mem_total else 0

        # CPU info
        cpu_model = platform.processor() or "x86_64 Processor"
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

        # EFI mode
        efi_status = "UEFI (Active)" if os.path.exists("/sys/firmware/efi") else "Legacy BIOS"

        return {
            "os_name": "Arvor Linux Recovery Mode",
            "build": self.build_version,
            "kernel": platform.release(),
            "cpu": cpu_model,
            "memory_total": f"{mem_total} MB",
            "memory_used": f"{mem_used} MB ({mem_pct:.1f}%)",
            "vg_name": "arvor_vg",
            "thin_pool": "Inspecting...",
            "efi_mode": efi_status,
            "recovery_part": "Auto-detected"
        }
