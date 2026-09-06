"""
Unit tests for DiskManager.
"""

import unittest
from core.disk import DiskManager


class TestDiskManager(unittest.TestCase):
    def setUp(self):
        self.dm = DiskManager(simulate=True)

    def test_list_block_devices(self):
        devs = self.dm.list_block_devices()
        self.assertIsInstance(devs, list)
        self.assertGreaterEqual(len(devs), 1)
        self.assertEqual(devs[0]["name"], "nvme0n1")

    def test_find_recovery_partition(self):
        rec = self.dm.find_recovery_partition()
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "nvme0n1p3")
        self.assertEqual(rec["fstype"], "ext4")

    def test_find_esp_partition(self):
        esp = self.dm.find_esp_partition()
        self.assertIsNotNone(esp)
        self.assertEqual(esp["name"], "nvme0n1p1")
        self.assertEqual(esp["fstype"], "vfat")

    def test_get_root_lvm_partition(self):
        lvm_part = self.dm.get_root_lvm_partition()
        self.assertIsNotNone(lvm_part)
        self.assertIn("nvme0n1p4", lvm_part)


if __name__ == "__main__":
    unittest.main()
