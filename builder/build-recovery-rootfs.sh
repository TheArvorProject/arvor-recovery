#!/usr/bin/env bash
# ==============================================================================
# Arvor Linux Recovery Mode - Standalone RootFS & SquashFS Builder
# Builds the lightweight independent recovery system for the dedicated partition
# ==============================================================================
set -e

WORK_DIR="/tmp/arvor_recovery_build"
TARGET_SQUASHFS="/tmp/arvor_recovery.squashfs"
ROOTFS_DIR="$WORK_DIR/rootfs"

echo -e "\033[1;36m==>\033[0m Preparing build environment in $WORK_DIR..."
rm -rf "$WORK_DIR"
mkdir -p "$ROOTFS_DIR"

# 1. Base Bootstrap or Minimal Skeleton
echo -e "\033[1;36m==>\033[0m Bootstrapping minimal recovery rootfs..."
if command -v debootstrap >/dev/null 2>&1; then
    debootstrap --variant=minbase --include=python3,lvm2,xfsprogs,e2fsprogs,parted,util-linux,pciutils,iproute2,systemd-sysv,bash,coreutils,kmod \
        trixie "$ROOTFS_DIR" http://deb.debian.org/debian
else
    echo -e "\033[1;33m[WARN]\033[0m debootstrap not found. Creating staging skeleton..."
    mkdir -p "$ROOTFS_DIR"/{bin,sbin,usr/bin,usr/sbin,etc,proc,sys,dev,tmp,run,mnt}
fi

# 2. Install Arvor Recovery binaries and libraries
echo -e "\033[1;36m==>\033[0m Installing Arvor Recovery application..."
RECOVERY_SRC="$(dirname "$0")/.."
mkdir -p "$ROOTFS_DIR/usr/lib/arvor-recovery"
cp -a "$RECOVERY_SRC/core" "$ROOTFS_DIR/usr/lib/arvor-recovery/"
cp -a "$RECOVERY_SRC/ui" "$ROOTFS_DIR/usr/lib/arvor-recovery/"
cp "$RECOVERY_SRC/bin/arvor-recovery" "$ROOTFS_DIR/usr/bin/arvor-recovery"
chmod +x "$ROOTFS_DIR/usr/bin/arvor-recovery"

# 3. Configure Autologin on TTY1 directly into arvor-recovery
echo -e "\033[1;36m==>\033[0m Configuring autologin service into Arvor Recovery..."
mkdir -p "$ROOTFS_DIR/etc/systemd/system/getty@tty1.service.d"
cat << 'EOF' > "$ROOTFS_DIR/etc/systemd/system/getty@tty1.service.d/override.conf"
[Service]
ExecStart=
ExecStart=-/usr/bin/arvor-recovery
StandardInput=tty
StandardOutput=tty
Restart=always
RestartSec=1
EOF

# 4. Compress to SquashFS
echo -e "\033[1;36m==>\033[0m Generating SquashFS image: $TARGET_SQUASHFS..."
if command -v mksquashfs >/dev/null 2>&1; then
    mksquashfs "$ROOTFS_DIR" "$TARGET_SQUASHFS" -comp xz -noappend -processors 4
    echo -e "\033[1;32m✔\033[0m Recovery SquashFS generated successfully: $TARGET_SQUASHFS"
else
    echo -e "\033[1;33m[WARN]\033[0m mksquashfs not found. Please install squashfs-tools."
fi

echo -e "\033[1;32m==> Build finished.\033[0m"
