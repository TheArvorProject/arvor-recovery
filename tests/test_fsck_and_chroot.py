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
            root_lv="/dev/arvor_vg/root"
        )
        self.assertTrue(res)
        self.assertGreaterEqual(len(progress_records), 5)
        self.assertEqual(progress_records[-1][0], 100)


if __name__ == "__main__":
    unittest.main()
