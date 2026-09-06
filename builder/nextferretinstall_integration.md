# Guia de Integração do Recovery Mode no Instalador (`nextferretinstall`)

Para habilitar a criação automática da partição de recuperação durante a instalação do Arvor Linux, as seguintes modificações devem ser aplicadas no script de instalação (`arvor-main/usr/bin/nextferretinstall`):

---

## 1. Ajuste do Esquema de Particionamento

No método de particionamento (em torno da linha 355 de `nextferretinstall`), adicione a partição dedicada `RECOVERY` antes do LVM:

```python
# Particionamento GPT
self.run_cmd(f"parted -s {d} mklabel gpt")
self.run_cmd(f"parted -s {d} mkpart ESP fat32 1MiB 513MiB")
self.run_cmd(f"parted -s {d} set 1 esp on")
self.run_cmd(f"parted -s {d} mkpart BOOT ext4 513MiB 1537MiB")
self.run_cmd(f"parted -s {d} mkpart RECOVERY ext4 1537MiB 6657MiB")   # 5GB dedicados ao Recovery (ext4 isolada fora do LVM)
self.run_cmd(f"parted -s {d} mkpart LVM 6657MiB 100%")                 # LVM ocupa o restante
```

E defina os dispositivos de partição:

```python
sep = "p" if "nvme" in d else ""
p1, p2, p3, p4 = f"{d}{sep}1", f"{d}{sep}2", f"{d}{sep}3", f"{d}{sep}4"

# Formatação das partições independentes:
self.run_cmd(f"mkfs.vfat -F32 {p1}")
self.run_cmd(f"mkfs.ext4 -F {p2}")
self.run_cmd(f"mkfs.ext4 -F -L ARVOR_RECOVERY {p3}")  # Label que o GRUB usa para localizar

# LVM agora utiliza a partição p4
lvm_dev = p4
```

---

## 2. Povoamento da Partição de Recuperação (Debootstrap & Standalone)

Após a criação do filesystem na partição `p3`:

```python
rec_mnt = "/mnt/recovery_staging"
os.makedirs(rec_mnt, exist_ok=True)
self.run_cmd(f"mount {p3} {rec_mnt}")

# 1. Debootstrap minimal na partição de recuperação
self.run_cmd(f"debootstrap --variant=minbase --arch=amd64 --include=python3,python3-pyqt6,lvm2,xfsprogs,e2fsprogs,parted,util-linux,pciutils,iproute2,systemd-sysv,bash,coreutils,kmod,linux-image-amd64,sudo,rsync,grub-efi-amd64-signed trixie {rec_mnt} http://deb.debian.org/debian")

# 2. Configuração de credenciais padrão
self.run_cmd(f'chroot {rec_mnt} /bin/sh -c "echo \\"root:root\\" | chpasswd"')
self.run_cmd(f'chroot {rec_mnt} /bin/sh -c "id -u arvor >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo arvor && echo \\"arvor:arvor\\" | chpasswd"')

# 3. Instalação do Arvor Recovery GUI e Autologin
# Copia binários e módulos para rec_mnt
# Configura /etc/systemd/system/getty@tty1.service.d/override.conf para iniciar /usr/bin/arvor-recovery

self.run_cmd(f"umount {rec_mnt}")
```

---

## 3. Registro da Entrada UEFI no NVRAM

No bloco de configuração do bootloader (linhas 670–680):

```python
# Registra o sistema operacional normal
self.run_cmd(f'efibootmgr -c -d {self.conf["disk"]} -p 1 -L "Arvor Linux" -l "\\EFI\\arvor-linux\\grubx64.efi"')

# Registra a entrada dedicada de Recovery
self.run_cmd(f'efibootmgr -c -d {self.conf["disk"]} -p 1 -L "Arvor Linux Recovery" -l "\\EFI\\arvor-recovery\\grubx64.efi"')
```

Dessa forma, caso o sistema principal seja danificado ou o Thin Pool trave, a entrada "Arvor Linux Recovery" estará presente no menu de boot da BIOS/UEFI e iniciará o ambiente de recuperação isoladamente.
