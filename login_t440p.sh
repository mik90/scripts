#!/bin/sh

if [ ! "$(ls -A $DIR)" ]; then
  # Directory is empty, so mount OneDrive
  rclone --vfs-cache-mode writes mount onedrive: ~/OneDrive &
fi

sudo /home/mike/Development/scripts/set_t440p_backlight.sh 2700

