# Arvor Linux Recovery Mode

**Arvor Linux Recovery Mode** is a dedicated, standalone graphical rescue and recovery environment for the [Arvor Linux](https://github.com/NextFerret/arvor) operating system. Inspired by **Android Recovery (TWRP)** and modern **UEFI firmware recovery (like Dell SupportAssist / macOS Recovery)**, it operates in complete isolation from the primary system's LVM storage pool.

---

## Key Features

1. **100% Graphical Interface (Qt6 + Official SVG Vector Logo)**:
   - Built natively with **PyQt6 / PySide6**, rendering the authentic Arvor pine tree vector logo (`assets/arvor-tree.svg`) in crisp, full anti-aliased definition.
   - Dynamic typewriter boot sequence typing out build identification and security advisories letter by letter with a blinking cursor `█` (instant skip on any keypress or click).
   - Live command execution console (`QTextEdit`) streaming underlying LVM and system commands in real time with syntax highlighting.
2. **LVM Isolation & Safety**:
   - Installed on a dedicated **5GB `ext4`** partition (`ARVOR_RECOVERY`) completely outside the LVM Volume Group (`arvor_vg`), ensuring that filesystem repair, formatting, or snapshot merges can proceed even if the primary LVM thin pool locks up or crashes.
3. **Dedicated NVRAM UEFI Entry**:
   - Configured with its own independent EFI boot entry (`\EFI\arvor-recovery\grubx64.efi`), accessible directly from motherboard BIOS/UEFI boot menus even if the main OS bootloader is damaged.
4. **Snapshot Rollback & Lifecycle**:
   - Lists snapshots created on the system (e.g. by `arvorctl`).
   - One-click rollback (`lvconvert --merge`) to restore the system to a clean prior state.
   - Snapshot deletion with red safety warning dialogs to reclaim thin pool capacity.
5. **Rescue Chroot Shell**:
   - One-click automated mounting of root logical volumes, system pseudo-filesystems (`/dev`, `/proc`, `/sys`, `/run`, `/boot`), and DNS (`/etc/resolv.conf`) for rapid terminal rescue work.
6. **Non-Destructive Integrity Checking (`fsck`)**:
   - Automatic detection of XFS and Ext4 filesystems with safe inspection (`xfs_repair -n`, `e2fsck -n`) and repair facilities.
7. **Automated Factory Reinstallation**:
   - Restores the base OS from the recovery partition's bundled SquashFS image, formatting only the root logical volume while keeping the recovery partition untouched.

---

## Keyboard Controls

| Key | Action |
| --- | --- |
| `↑` / `↓` | Navigate menu options |
| `Enter` | Select / Confirm operation |
| `ESC` | Back to main menu / Dismiss dialog |
| `Mouse` | All buttons, menu items, and dialogs are also fully clickable |

---

## Project Structure

```
arvor-recovery-main/
├── assets/
│   ├── arvor-tree.svg            # Official Arvor Linux vector logo
│   └── arvor-tree.png            # High-res 512x512 raster logo
├── bin/
│   └── arvor-recovery            # Main executable entrypoint
├── core/
│   ├── disk.py                   # Storage device, ESP & partition discovery
│   ├── lvm.py                    # LVM Volume Group, Thin Pool & Snapshot engine
│   ├── fsck.py                   # Filesystem inspection and repair utilities
│   ├── chroot.py                 # Rescue chroot mounting & shell lifecycle
│   ├── reinstall.py              # Automated factory restore pipeline
│   └── sysinfo.py                # Hardware & system diagnostics
├── ui/
│   ├── __init__.py               # UI package entrypoint
│   ├── gui.py                    # 100% Graphical UEFI Recovery Interface
│   └── qt_compat.py              # Transparent PyQt6 / PySide6 compatibility layer
├── builder/
│   ├── build-recovery-rootfs.sh  # Minimal standalone SquashFS rootfs builder
│   ├── grub-recovery.cfg         # Dedicated GRUB configuration
│   ├── install-recovery-entry.sh # Script for efibootmgr NVRAM registration
│   └── nextferretinstall_integration.md # Guide to integrate 5GB partition into installer
└── tests/
    ├── test_disk.py
    ├── test_gui.py               # Headless automated GUI tests
    ├── test_lvm.py
    └── test_fsck_and_chroot.py
```

---

## Development & Testing

### Running in Simulation Mode (Safe, no root required)
```bash
make run-sim
# or:
./bin/arvor-recovery --simulate
```

### Running Automated Tests
```bash
make test
```

### Running in Live Mode (Requires root)
```bash
make run
# or:
sudo ./bin/arvor-recovery
```
