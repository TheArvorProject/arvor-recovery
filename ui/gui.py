"""
Arvor Linux Recovery Mode - Modern UEFI/Dell-style Graphical Interface.
Features authentic vector SVG logo, typewriter boot sequence, monospace typography,
live terminal console, snapshot selector with red highlight bar, and circular progress spinner.
"""

import os
import sys
import time
from typing import Optional, List, Tuple

from ui.qt_compat import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox, QTextEdit,
    QListWidget, QListWidgetItem, QFrame, QProgressBar, QDialog,
    Qt, QTimer, QThread, Signal, QSvgWidget
)
from core.disk import DiskManager
from core.lvm import LVMManager
from core.fsck import FsckManager
from core.chroot import ChrootManager
from core.reinstall import ReinstallManager
from core.sysinfo import SysInfoCollector


STYLESHEET = """
QMainWindow {
    background-color: #000000;
}
QWidget {
    font-family: "Consolas", "Liberation Mono", "Courier New", "DejaVu Sans Mono", monospace;
    font-size: 13px;
    color: #ffffff;
    background-color: #000000;
}

QListWidget {
    background-color: #000000;
    border: none;
    outline: none;
}
QListWidget::item {
    color: #4ac3ff;
    padding: 7px 14px;
    margin-bottom: 2px;
    border-radius: 2px;
}
QListWidget::item:hover {
    background-color: #112238;
    color: #ffffff;
}
QListWidget::item:selected {
    background-color: #ffffff;
    color: #000000;
    font-weight: bold;
}

/* Red selection for destructive actions like delete snapshot */
QListWidget[danger="true"]::item:selected {
    background-color: #cc2222;
    color: #ffffff;
    font-weight: bold;
}

QTextEdit {
    background-color: #040810;
    color: #00ff88;
    border: 1px solid #1a2a40;
    border-radius: 4px;
    font-family: "Consolas", "Liberation Mono", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
    line-height: 1.4;
}

QProgressBar {
    border: 1px solid #224466;
    background-color: #0d1a2d;
    height: 18px;
    border-radius: 3px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #4a9eff;
}

QPushButton {
    background-color: #162238;
    color: #ffffff;
    border: 1px solid #2c4466;
    padding: 8px 22px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #22385c;
    border-color: #4a9eff;
}
QPushButton[danger="true"] {
    background-color: #aa1111;
    border-color: #ff3333;
}
QPushButton[danger="true"]:hover {
    background-color: #cc2222;
}
"""


class DangerDialog(QDialog):
    def __init__(self, title: str, warning_lines: list, target_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(640, 250)
        self.setStyleSheet("background-color: #0d0000; border: 2px solid #cc2222;")
        layout = QVBoxLayout(self)

        lbl_title = QLabel("WARNING: THIS WILL PERMANENTLY ALTER DISK DATA!")
        lbl_title.setStyleSheet("color: #ff3333; font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl_title)

        for line in warning_lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("color: #ff8888; font-size: 13px;")
            layout.addWidget(lbl)

        lbl_target = QLabel(f"Target: {target_name}")
        lbl_target.setStyleSheet("color: #ffff00; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_target)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel [Esc]")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("Confirm Execution [Enter]")
        self.btn_confirm.setProperty("danger", "true")
        self.btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class RecoveryMainWindow(QMainWindow):
    def __init__(self, simulate: bool = False):
        super().__init__()
        self.simulate = simulate
        self.active_vg = "arvor_vg"

        # Engine instances
        self.disk_mgr = DiskManager(simulate=simulate, logger=self.append_log)
        self.lvm_mgr = LVMManager(simulate=simulate, logger=self.append_log)
        self.fsck_mgr = FsckManager(simulate=simulate, logger=self.append_log)
        self.chroot_mgr = ChrootManager(simulate=simulate, logger=self.append_log)
        self.reinstall_mgr = ReinstallManager(simulate=simulate, logger=self.append_log, progress_cb=self.on_progress)
        self.sysinfo = SysInfoCollector(simulate=simulate)

        self.setWindowTitle("Arvor Linux Recovery Mode")
        self.setMinimumSize(980, 700)
        self.setStyleSheet(STYLESHEET)

        # Typewriter animation state
        self.animating = True
        self.type_queue: List[Tuple[QLabel, str]] = []
        self.current_type_idx = 0
        self.current_char_idx = 0
        self.menu_items_queue: List[str] = []

        self.init_ui()
        self.setup_typewriter_animation()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(22, 16, 22, 16)
        root_layout.setSpacing(10)

        # 1. Top Header Bar
        header_layout = QHBoxLayout()
        self.lbl_header_left = QLabel("Arvor Recovery Mode (LVM)")
        self.lbl_header_left.setStyleSheet("color: #4ac3ff; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.lbl_header_left)

        header_layout.addStretch()

        self.lbl_header_right = QLabel(f"{self.sysinfo.build_version} | Volume Group: {self.active_vg}")
        self.lbl_header_right.setStyleSheet("color: #4ac3ff; font-size: 13px;")
        header_layout.addWidget(self.lbl_header_right)
        root_layout.addLayout(header_layout)

        # Sub-header: status, thin pool, badges
        pool_info = self.lvm_mgr.get_thin_pool_info(self.active_vg)
        pool_str = f"Thin Pool: {pool_info['data_percent']}% Data | {pool_info['metadata_percent']}% Meta" if pool_info else "Thin Pool: Active"
        self.lbl_sub = QLabel(f"Status: {'[SIMULATION MODE]' if self.simulate else '[LIVE RECOVERY]'} | {pool_str}  [UEFI x86_64]")
        self.lbl_sub.setStyleSheet("color: #ffff00; font-size: 12px;")
        root_layout.addWidget(self.lbl_sub)

        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #4ac3ff; background-color: #224466; max-height: 1px;")
        root_layout.addWidget(line)

        # 2. Stacked Content Area (Main Menu vs Subviews)
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.view_main = self.create_main_menu_view()
        self.stack.addWidget(self.view_main)

        self.view_snapshots = self.create_snapshot_view()
        self.stack.addWidget(self.view_snapshots)

        self.view_progress = self.create_progress_view()
        self.stack.addWidget(self.view_progress)

        # 3. Bottom Live Log Console
        lbl_console_title = QLabel("── LIVE LOG CONSOLE / TERMINAL OUTPUT ──────────────────────────────────────────")
        lbl_console_title.setStyleSheet("color: #8899aa; font-size: 11px; margin-top: 5px;")
        root_layout.addWidget(lbl_console_title)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(145)
        root_layout.addWidget(self.log_console)

    def create_main_menu_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Hero section: Logo + Title Box
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(25)

        # Official Arvor SVG Tree Logo
        svg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "arvor-tree.svg")
        if os.path.exists(svg_path):
            self.svg_logo = QSvgWidget(svg_path)
            self.svg_logo.setFixedSize(130, 130)
            self.svg_logo.setStyleSheet("background: transparent;")
            hero_layout.addWidget(self.svg_logo)
        else:
            lbl_fallback = QLabel("▲\n▲▲\n▲▲▲")
            lbl_fallback.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
            hero_layout.addWidget(lbl_fallback)

        # Text labels for Typewriter Effect
        title_box = QVBoxLayout()
        title_box.setSpacing(5)

        self.lbl_detected = QLabel("")
        self.lbl_detected.setStyleSheet("color: #ffff00; font-size: 13px;")
        title_box.addWidget(self.lbl_detected)

        self.lbl_main_title = QLabel("")
        self.lbl_main_title.setStyleSheet("color: #ffff00; font-size: 22px; font-weight: bold;")
        title_box.addWidget(self.lbl_main_title)

        self.lbl_warning = QLabel("")
        self.lbl_warning.setStyleSheet("color: #ff3333; font-size: 12px; font-weight: 500;")
        self.lbl_warning.setWordWrap(True)
        title_box.addWidget(self.lbl_warning)

        hero_layout.addLayout(title_box, stretch=1)
        layout.addLayout(hero_layout)

        # Menu List Widget (initially hidden/empty during typewriter animation)
        self.menu_list = QListWidget()
        self.full_menu_items = [
            "Reboot The System Now",
            "Format The System Using a defined Hard Drive And Reinstall Arvor Linux (won't touch the Recovery Partition)",
            "Merge a System Snapshot Using a Defined Partition",
            "Delete a Snapshot",
            "Chroot into a LVM Logical Volume in a Defined Partition",
            "Volume Check (fsck / xfs_repair)",
            "System Info & Thin Pool Diagnostics",
            "Exit Recovery to Emergency Shell"
        ]
        self.menu_list.itemActivated.connect(self.handle_menu_selection)
        layout.addWidget(self.menu_list, stretch=1)

        # Prompt
        self.lbl_prompt = QLabel("")
        self.lbl_prompt.setStyleSheet("color: #8899aa; font-size: 12px;")
        layout.addWidget(self.lbl_prompt)

        return widget

    def setup_typewriter_animation(self):
        """Prepares the typewriter sequence for the text opening effect."""
        build_str = self.sysinfo.build_version.replace("Build ", "")
        self.text_detected = f"Detected Running Arvor Linux Recovery Mode Build {build_str}"
        self.text_title = "Arvor Linux Recovery Mode"
        self.text_warning = (
            "Warning: Using some functions in this recovery mode may format your\n"
            "files on the Arvor Linux partition."
        )
        self.text_prompt = "change options Using Arrow Keys, Use Enter to confirm."

        self.type_queue = [
            (self.lbl_detected, self.text_detected),
            (self.lbl_main_title, self.text_title),
            (self.lbl_warning, self.text_warning)
        ]
        self.current_type_idx = 0
        self.current_char_idx = 0
        self.menu_items_queue = list(self.full_menu_items)

        # Timer for typing characters
        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self.tick_typewriter)
        self.type_timer.start(14)  # 14ms per character: smooth, crisp cadence

    def tick_typewriter(self):
        """Advances one character in the typewriter sequence."""
        if not self.animating:
            return

        if self.current_type_idx < len(self.type_queue):
            label, full_text = self.type_queue[self.current_type_idx]
            self.current_char_idx += 1
            typed_part = full_text[:self.current_char_idx]

            # Append blinking cursor during typing
            cursor = "█" if (self.current_char_idx % 4 < 2) else " "
            label.setText(typed_part + cursor)

            if self.current_char_idx >= len(full_text):
                label.setText(full_text)  # Remove cursor from finished field
                self.current_type_idx += 1
                self.current_char_idx = 0
        else:
            # All headers typed! Switch to sequential menu item cascade
            self.type_timer.stop()
            self.cascade_menu_timer = QTimer(self)
            self.cascade_menu_timer.timeout.connect(self.tick_menu_cascade)
            self.cascade_menu_timer.start(45)

    def tick_menu_cascade(self):
        """Sequentially reveals menu options line by line."""
        if not self.animating:
            return

        if self.menu_items_queue:
            item_text = self.menu_items_queue.pop(0)
            self.menu_list.addItem(item_text)
        else:
            self.cascade_menu_timer.stop()
            self.lbl_prompt.setText(self.text_prompt)
            self.menu_list.setCurrentRow(0)
            self.menu_list.setFocus()
            self.animating = False
            self.start_initial_scan()

    def skip_animation(self):
        """Instantly skips the typewriter animation on any user interaction."""
        if not self.animating:
            return
        self.animating = False

        if hasattr(self, 'type_timer') and self.type_timer.isActive():
            self.type_timer.stop()
        if hasattr(self, 'cascade_menu_timer') and self.cascade_menu_timer.isActive():
            self.cascade_menu_timer.stop()

        # Instantly fill all texts
        self.lbl_detected.setText(self.text_detected)
        self.lbl_main_title.setText(self.text_title)
        self.lbl_warning.setText(self.text_warning)
        self.lbl_prompt.setText(self.text_prompt)

        # Instantly populate menu
        self.menu_list.clear()
        for it in self.full_menu_items:
            self.menu_list.addItem(it)

        self.menu_list.setCurrentRow(0)
        self.menu_list.setFocus()
        self.start_initial_scan()

    def create_snapshot_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_snap_title = QLabel("CR snapshot logical volume to DELETE:")
        self.lbl_snap_title.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_snap_title)

        self.snap_list = QListWidget()
        self.snap_list.setProperty("danger", "true")
        self.snap_list.itemActivated.connect(self.handle_snapshot_selection)
        layout.addWidget(self.snap_list, stretch=1)

        btn_layout = QHBoxLayout()
        btn_back = QPushButton("Back [Esc]")
        btn_back.clicked.connect(self.return_to_main_menu)
        btn_layout.addWidget(btn_back)
        btn_layout.addStretch()

        self.btn_action_snap = QPushButton("Confirm Selection [Enter]")
        self.btn_action_snap.setProperty("danger", "true")
        self.btn_action_snap.clicked.connect(lambda: self.handle_snapshot_selection(self.snap_list.currentItem()))
        btn_layout.addWidget(self.btn_action_snap)

        layout.addLayout(btn_layout)
        return widget

    def create_progress_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        self.lbl_progress_spin = QLabel("◓ 75%")
        self.lbl_progress_spin.setStyleSheet("color: #4ac3ff; font-size: 32px; font-weight: bold;")
        self.lbl_progress_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_progress_spin)

        self.lbl_progress_desc = QLabel("Processing operation...")
        self.lbl_progress_desc.setStyleSheet("color: #ffffff; font-size: 14px;")
        self.lbl_progress_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_progress_desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(440)
        self.progress_bar.setValue(75)
        layout.addWidget(self.progress_bar)

        return widget

    def append_log(self, text: str):
        if hasattr(self, 'log_console'):
            self.log_console.append(text)
            sb = self.log_console.verticalScrollBar()
            sb.setValue(sb.maximum())

    def on_progress(self, percent: int, desc: str):
        if hasattr(self, 'lbl_progress_spin'):
            spinner_icons = ["◐", "◓", "◑", "◒"]
            icon = spinner_icons[(percent // 5) % len(spinner_icons)]
            self.lbl_progress_spin.setText(f"{icon} {percent}%")
            self.lbl_progress_desc.setText(desc)
            self.progress_bar.setValue(percent)
        QApplication.processEvents()

    def start_initial_scan(self):
        if not hasattr(self, '_initial_scan_done'):
            self._initial_scan_done = True
            self.append_log("Initializing Arvor Linux Recovery Environment...")
            self.append_log(f"Detected Running Arvor Linux Recovery Mode Build {self.sysinfo.build_version.replace('Build ', '')}")
            self.lvm_mgr.activate_vgs()
            self.append_log("Scanning storage devices and snapshots...")
            self.append_log("System ready. Use Arrow Keys to select an option and Enter to execute.")

    def handle_menu_selection(self, item: QListWidgetItem):
        row = self.menu_list.row(item)
        if row == 0:  # Reboot
            dlg = DangerDialog(
                title="System Reboot",
                warning_lines=["You are about to reboot the computer.", "Any temporary session state will be discarded."],
                target_name="System Hardware",
                parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.append_log("Reboot authorized. Restarting system...")
                if not self.simulate:
                    os.system("sync; reboot")
                else:
                    self.append_log("[SIMULATION] sync; reboot command dispatched.")

        elif row == 1:  # Reinstall
            dlg = DangerDialog(
                title="Factory Reinstall Arvor Linux",
                warning_lines=[
                    "THIS WILL FORMAT AND REINSTALL THE ROOT SYSTEM!",
                    "All user data on the main system partition will be replaced.",
                    "The dedicated Recovery Partition will remain untouched."
                ],
                target_name=f"/dev/{self.active_vg}/root",
                parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.stack.setCurrentIndex(2)
                self.reinstall_mgr.reinstall_system(
                    disk_dev="/dev/nvme0n1",
                    recovery_part="/dev/nvme0n1p3",
                    root_lv=f"/dev/{self.active_vg}/root"
                )
                self.stack.setCurrentIndex(0)
                QMessageBox.information(
                    self, "Reinstall Complete",
                    "Arvor Linux was successfully restored from recovery storage!\nPress OK to return to main menu."
                )

        elif row == 2:  # Merge snapshot
            self.current_snap_action = "merge"
            self.lbl_snap_title.setText("Select snapshot logical volume to MERGE (revert system):")
            self.lbl_snap_title.setStyleSheet("color: #4ac3ff; font-weight: bold; font-size: 14px;")
            self.btn_action_snap.setText("Merge Snapshot [Enter]")
            self.btn_action_snap.setProperty("danger", "false")
            self.populate_snapshots()
            self.stack.setCurrentIndex(1)

        elif row == 3:  # Delete snapshot
            self.current_snap_action = "delete"
            self.lbl_snap_title.setText("CR snapshot logical volume to DELETE:")
            self.lbl_snap_title.setStyleSheet("color: #ff3333; font-weight: bold; font-size: 14px;")
            self.btn_action_snap.setText("Delete Snapshot [Enter]")
            self.btn_action_snap.setProperty("danger", "true")
            self.populate_snapshots()
            self.stack.setCurrentIndex(1)

        elif row == 4:  # Chroot
            self.append_log(f"Preparing rescue chroot into /dev/{self.active_vg}/root...")
            self.chroot_mgr.prepare_and_enter(f"/dev/{self.active_vg}/root")

        elif row == 5:  # fsck
            self.append_log(f"Starting volume integrity check on /dev/{self.active_vg}/root...")
            res = self.fsck_mgr.check_volume(f"/dev/{self.active_vg}/root", repair=False)
            QMessageBox.information(
                self, "Filesystem Check Complete",
                f"Target: {res['dev']}\nType: {res['fstype']}\nStatus: {res['status'].upper()}\n\n{res.get('output', '')[:300]}"
            )

        elif row == 6:  # System Info
            info = self.sysinfo.get_system_summary()
            pool = self.lvm_mgr.get_thin_pool_info(self.active_vg)
            pool_str = f"{pool['name']} ({pool['data_percent']}% Data, {pool['metadata_percent']}% Meta)" if pool else "N/A"
            msg = (
                f"Operating System: {info['os_name']}\n"
                f"Build Version:    {info['build']}\n"
                f"Kernel Release:   {info['kernel']}\n"
                f"CPU Hardware:     {info['cpu']}\n"
                f"System Memory:    {info['memory_used']} of {info['memory_total']}\n"
                f"Boot Mode:        {info['efi_mode']}\n"
                f"Volume Group:     {self.active_vg}\n"
                f"Thin Pool:        {pool_str}\n"
                f"Recovery Device:  {info['recovery_part']}"
            )
            QMessageBox.information(self, "System Information & Diagnostics", msg)

        elif row == 7:  # Exit
            self.close()

    def populate_snapshots(self):
        self.snap_list.clear()
        snaps = self.lvm_mgr.list_snapshots(self.active_vg)
        for s in snaps:
            name = f"{s['vg_name']}/{s['lv_name']}"
            it = QListWidgetItem(f"  {name:<32} [Origin: {s['origin']} | Delta: {s['data_percent']}% | Date: {s['lv_time']}]")
            it.setData(Qt.ItemDataRole.UserRole, s)
            self.snap_list.addItem(it)

        if self.snap_list.count() > 0:
            self.snap_list.setCurrentRow(0)

    def handle_snapshot_selection(self, item: Optional[QListWidgetItem]):
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        target_name = f"{data['vg_name']}/{data['lv_name']}"

        if getattr(self, 'current_snap_action', 'delete') == 'delete':
            dlg = DangerDialog(
                title="Permanent Snapshot Deletion",
                warning_lines=[
                    "THIS WILL PERMANENTLY ERASE THE SNAPSHOT DATA!",
                    "The storage occupied by this snapshot will be returned to the thin pool."
                ],
                target_name=target_name,
                parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.lvm_mgr.delete_snapshot(data['vg_name'], data['lv_name'])
                self.populate_snapshots()
        else:
            dlg = DangerDialog(
                title="Confirm Snapshot Rollback",
                warning_lines=[
                    f"You are about to roll back the system to '{target_name}'.",
                    "Modifications made after this snapshot was created will be replaced."
                ],
                target_name=target_name,
                parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.lvm_mgr.merge_snapshot(data['vg_name'], data['lv_name'])
                self.return_to_main_menu()

    def return_to_main_menu(self):
        self.stack.setCurrentIndex(0)

    def keyPressEvent(self, event):
        if self.animating:
            self.skip_animation()
            return

        if event.key() == Qt.Key.Key_Escape:
            if self.stack.currentIndex() != 0:
                self.return_to_main_menu()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.animating:
            self.skip_animation()
            return
        super().mousePressEvent(event)


def run_gui(simulate: bool = False):
    app = QApplication.instance() or QApplication(sys.argv)
    window = RecoveryMainWindow(simulate=simulate)
    window.show()
    return app.exec()
