#!/bin/sh

ONEDRIVE_DIR="/home/mike/OneDrive"
if [ ! "$(ls -A $ONEDRIVE_DIR)" ]; then
  # Directory is empty, so mount OneDrive
  rclone --vfs-cache-mode writes mount onedrive: $ONEDRIVE_DIR &
fi

#sudo /home/mike/Development/scripts/set_t440p_backlight.sh 2300

