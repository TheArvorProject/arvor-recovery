"""
Unit tests for FsckManager and ChrootManager.
"""

import unittest
from core.fsck import FsckManager
from core.chroot import ChrootManager
from core.reinstall import ReinstallManager


class TestSystemManagers(unittest.TestCase):
    def setUp(self):
        self.logs = []

    def test_fsck_simulate(self):
        fsck = FsckManager(simulate=True, logger=self.logs.append)
        res = fsck.check_volume("/dev/arvor_vg/root")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "clean")

    def test_chroot_simulate(self):
        chroot = ChrootManager(simulate=True, logger=self.logs.append)
        res = chroot.prepare_and_enter("/dev/arvor_vg/root")
        self.assertTrue(res)

    def test_reinstall_simulate(self):
        progress_records = []
        reinst = ReinstallManager(
            simulate=True,
            logger=self.logs.append,
            progress_cb=lambda pct, desc: progress_records.append((pct, desc))
        )
        res = reinst.reinstall_system(
            disk_dev="/dev/nvme0n1",
            recovery_part="/dev/nvme0n1p3",
            root_lv="/dev/arvor_vg/root",
            default_user="arvor",
            default_user_pass="arvor",
            root_pass="root"
        )
        self.assertTrue(res)
        self.assertGreaterEqual(len(progress_records), 5)
        self.assertEqual(progress_records[-1][0], 100)
        self.assertTrue(any("arvor" in desc for _, desc in progress_records))

    def test_reinstall_rsync_excludes(self):
        reinst = ReinstallManager(simulate=True)
        excludes = reinst.get_rsync_excludes()
        self.assertIn("/usr/bin/arvor-recovery", excludes)
        self.assertIn("/usr/lib/arvor-recovery", excludes)
        self.assertIn("/proc/*", excludes)
        self.assertIn("/sys/*", excludes)
        self.assertIn("/dev/*", excludes)

    def test_reinstall_mock_real_execution(self):
        from unittest.mock import patch, MagicMock
        reinst = ReinstallManager(simulate=False, logger=self.logs.append)
        with patch("subprocess.run") as mock_run, \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"):
            mock_run.return_value = MagicMock(returncode=0)
            success = reinst.reinstall_system(
                disk_dev="/dev/sda",
                recovery_part="/dev/sda3",
                root_lv="/dev/arvor_vg/root",
                default_user="arvor",
                default_user_pass="arvor",
                root_pass="root"
            )
            self.assertTrue(success)
            # Ensure rsync was called with excludes and root:root / user setup
            called_cmds = [call.args[0] for call in mock_run.call_args_list]
            self.assertTrue(any("mkfs.xfs" in str(cmd) for cmd in called_cmds))
            self.assertTrue(any("rsync" in str(cmd) for cmd in called_cmds))
            self.assertTrue(any("root:root" in str(cmd) for cmd in called_cmds))
            self.assertTrue(any("arvor:arvor" in str(cmd) for cmd in called_cmds))


if __name__ == "__main__":
    unittest.main()
