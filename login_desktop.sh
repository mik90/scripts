#!/bin/sh

if [ ! "$(ls -A $DIR)" ]; then
  # Directory is empty, so mount OneDrive
  rclone --vfs-cache-mode writes mount onedrive: ~/OneDrive &
fi
