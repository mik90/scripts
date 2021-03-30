#!/bin/bash

set -x

xrandr --output HDMI-0 --off
sleep 30s
xrandr --output DP-0 --primary --auto --output HDMI-0 --left-of DP-0 --auto 

# Set DP-0 as primary

