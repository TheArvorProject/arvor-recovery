"""
Unit tests for LVMManager.
"""

import unittest
from core.lvm import LVMManager


class TestLVMManager(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.lvm = LVMManager(simulate=True, logger=self.logs.append)

    def test_list_vgs(self):
        vgs = self.lvm.list_vgs()
        self.assertEqual(len(vgs), 1)
        self.assertEqual(vgs[0]["vg_name"], "arvor_vg")

    def test_thin_pool_info(self):
        pool = self.lvm.get_thin_pool_info("arvor_vg")
        self.assertIsNotNone(pool)
        self.assertEqual(pool["name"], "arvor_thin_pool")
        self.assertIn("data_percent", pool)

    def test_list_snapshots(self):
        snaps = self.lvm.list_snapshots("arvor_vg")
        self.assertGreaterEqual(len(snaps), 3)
        snap_root = next((s for s in snaps if s["lv_name"] == "snap_root_2026_09_01"), None)
        self.assertIsNotNone(snap_root)

    def test_delete_snapshot(self):
        initial_count = len(self.lvm.list_snapshots("arvor_vg"))
        success = self.lvm.delete_snapshot("arvor_vg", "snap_var_2026_07_30")
        self.assertTrue(success)
        new_count = len(self.lvm.list_snapshots("arvor_vg"))
        self.assertEqual(new_count, initial_count - 1)

    def test_create_snapshot(self):
        initial_count = len(self.lvm.list_snapshots("arvor_vg"))
        success = self.lvm.create_snapshot("arvor_vg", "root", "test_snap_01")
        self.assertTrue(success)
        new_count = len(self.lvm.list_snapshots("arvor_vg"))
        self.assertEqual(new_count, initial_count + 1)

    def test_merge_snapshot(self):
        success = self.lvm.merge_snapshot("arvor_vg", "snap_root_2026_09_01")
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
