#!/bin/bash
set -eux

# ensure GRUB is properly configured for SCSI disks
# this helps avoid issues where GRUB can't find the boot disk after VM creation
apt-get install -y grub-efi-amd64
if [ -f /sys/firmware/efi ]; then
    # UEFI system - reinstall grub to ensure proper disk references
    grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=proxmox --recheck
else
    # BIOS system - reinstall grub to MBR
    grub-install /dev/sda --recheck
fi

update-grub