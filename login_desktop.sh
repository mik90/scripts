#!/bin/sh

NOTES_DIR = "~/OneDrive"
if [ ! "$(ls -A $NOTES_DIR)" ]; then
  # Directory is empty, so mount OneDrive
  rclone --vfs-cache-mode writes mount onedrive: $NOTES_DIR &
fi

