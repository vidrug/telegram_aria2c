#!/bin/bash
# Auto-mount / unmount USB drives to /mnt/<label|device>
# Called by udev rule: 99-usb-automount.rules

ACTION=$1
DEVICE=$2
MOUNT_BASE="/mnt"

log() { logger -t usb-mount "$@"; }

case "$ACTION" in
    mount)
        # Skip if already mounted
        findmnt -rno TARGET "/dev/$DEVICE" &>/dev/null && exit 0

        LABEL=$(blkid -s LABEL -o value "/dev/$DEVICE" 2>/dev/null)
        MOUNT_POINT="$MOUNT_BASE/${LABEL:-$DEVICE}"

        mkdir -p "$MOUNT_POINT"

        FSTYPE=$(blkid -s TYPE -o value "/dev/$DEVICE" 2>/dev/null)
        case "$FSTYPE" in
            vfat|exfat)
                mount -t "$FSTYPE" -o rw,sync,uid=1000,gid=1000,umask=000 "/dev/$DEVICE" "$MOUNT_POINT"
                ;;
            ntfs|ntfs-3g)
                mount -t ntfs-3g -o rw,sync,uid=1000,gid=1000,umask=000 "/dev/$DEVICE" "$MOUNT_POINT"
                ;;
            *)
                mount -o rw,sync "/dev/$DEVICE" "$MOUNT_POINT"
                ;;
        esac

        if [ $? -eq 0 ]; then
            log "Mounted /dev/$DEVICE -> $MOUNT_POINT ($FSTYPE)"
        else
            log "Failed to mount /dev/$DEVICE"
            rmdir "$MOUNT_POINT" 2>/dev/null
        fi
        ;;

    unmount)
        MOUNT_POINT=$(findmnt -rno TARGET "/dev/$DEVICE" 2>/dev/null)
        if [ -n "$MOUNT_POINT" ]; then
            umount -l "$MOUNT_POINT"
            rmdir "$MOUNT_POINT" 2>/dev/null
            log "Unmounted /dev/$DEVICE from $MOUNT_POINT"
        fi
        ;;
esac
