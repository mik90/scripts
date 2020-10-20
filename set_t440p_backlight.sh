#!/bin/bash
# 2700 is mediumish
# 3700 is more than mediumish
echo $@ > /sys/class/backlight/intel_backlight/brightness

