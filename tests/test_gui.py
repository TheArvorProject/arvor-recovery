"""
Unit tests for the Graphical Recovery Mode Interface.
"""

import os
import unittest
from ui.qt_compat import QApplication
from ui.gui import RecoveryMainWindow

# Create headless QApplication for tests
app = QApplication.instance() or QApplication(["arvor-recovery-test", "-platform", "offscreen"])


class TestRecoveryGUI(unittest.TestCase):
    def setUp(self):
        self.window = RecoveryMainWindow(simulate=True)

    def test_window_initialization(self):
        self.assertIsNotNone(self.window)
        self.assertEqual(self.window.windowTitle(), "Arvor Linux Recovery Mode")

    def test_svg_logo_loaded(self):
        svg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "arvor-tree.svg")
        self.assertTrue(os.path.exists(svg_path))
        self.assertIsNotNone(self.window.svg_logo)

    def test_menu_items(self):
        self.assertGreaterEqual(len(self.window.full_menu_items), 7)
        self.assertIn("Reboot The System Now", self.window.full_menu_items[0])
        self.assertIn("Format The System", self.window.full_menu_items[1])
        self.assertIn("Merge a System Snapshot", self.window.full_menu_items[2])

    def test_skip_animation(self):
        self.window.skip_animation()
        self.assertFalse(self.window.animating)
        self.assertEqual(self.window.menu_list.count(), len(self.window.full_menu_items))
        self.assertEqual(self.window.menu_list.currentRow(), 0)

    def tearDown(self):
        self.window.close()


if __name__ == "__main__":
    unittest.main()
