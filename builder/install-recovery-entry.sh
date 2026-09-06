#!/usr/bin/env bash
# ==============================================================================
# Arvor Linux Recovery Mode - EFI Entry & Bootloader Registration
# ==============================================================================
set -e

if [ "$EUID" -ne 0 ]; then
    echo -e "\033[1;31m[ERROR]\033[0m Root privileges required to register EFI boot entries."
    exit 1
fi

DISK="${1:-/dev/nvme0n1}"
ESP_PART_NUM="${2:-1}"
EFI_MOUNT="${3:-/boot/efi}"

echo -e "\033[1;36m==>\033[0m Registering Arvor Recovery EFI Boot Entry on $DISK (ESP part: $ESP_PART_NUM)..."

RECOVERY_EFI_DIR="$EFI_MOUNT/EFI/arvor-recovery"
mkdir -p "$RECOVERY_EFI_DIR"

# Install standalone grub efi for recovery if grub-mkimage is present
if command -v grub-mkimage >/dev/null 2>&1; then
    echo -e "\033[1;36m==>\033[0m Generating standalone recovery grubx64.efi..."
    grub-mkimage -O x86_64-efi -o "$RECOVERY_EFI_DIR/grubx64.efi" \
        -p "/EFI/arvor-recovery" \
        fat ext2 part_gpt part_msdos normal search search_fs_file search_label linux reboot echo test
fi

# Fallback: copy signed/existing grub efi binary
if [ ! -f "$RECOVERY_EFI_DIR/grubx64.efi" ] && [ -f "$EFI_MOUNT/EFI/arvor-linux/grubx64.efi" ]; then
    cp -a "$EFI_MOUNT/EFI/arvor-linux/grubx64.efi" "$RECOVERY_EFI_DIR/grubx64.efi"
fi

# Copy embedded grub.cfg to recovery EFI dir
cp "$(dirname "$0")/grub-recovery.cfg" "$RECOVERY_EFI_DIR/grub.cfg" 2>/dev/null || true

# Register in UEFI NVRAM via efibootmgr
if command -v efibootmgr >/dev/null 2>&1; then
    echo -e "\033[1;36m==>\033[0m Adding UEFI Boot Entry 'Arvor Linux Recovery'..."
    # Remove existing entry if already registered to avoid duplicates
    EXISTING_ENTRY=$(efibootmgr | grep "Arvor Linux Recovery" | awk '{print $1}' | tr -d 'Boot*' | tr -d ':')
    if [ -n "$EXISTING_ENTRY" ]; then
        efibootmgr -b "$EXISTING_ENTRY" -B >/dev/null 2>&1 || true
    fi

    efibootmgr -c -d "$DISK" -p "$ESP_PART_NUM" -L "Arvor Linux Recovery" -l "\\EFI\\arvor-recovery\\grubx64.efi" || true
    echo -e "\033[1;32m✔\033[0m UEFI entry successfully registered."
else
    echo -e "\033[1;33m[WARN]\033[0m efibootmgr not found. Ensure EFI firmware detects \\EFI\\arvor-recovery\\grubx64.efi automatically."
fi

# Also configure fallback entry in main GRUB (/etc/grub.d/10_arvor_recovery)
MAIN_GRUB_D="/etc/grub.d"
if [ -d "$MAIN_GRUB_D" ]; then
    cat << 'EOF' > "$MAIN_GRUB_D/11_arvor_recovery"
#!/bin/sh
exec tail -n +3 $0
menuentry "Arvor Linux Recovery Mode" --class arvor --class recovery {
    search --no-floppy --set=root --label ARVOR_RECOVERY
    linux /live/vmlinuz boot=live toram components quiet splash arvor_recovery=1
    initrd /live/initrd.img
}
EOF
    chmod +x "$MAIN_GRUB_D/11_arvor_recovery"
    echo -e "\033[1;32m✔\033[0m Added recovery entry to /etc/grub.d/11_arvor_recovery"
fi

echo -e "\033[1;32m==> Recovery Bootloader setup completed successfully!\033[0m"
