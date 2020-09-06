#!/bin/bash

WORKSPACES_DIR=/home/mike/Development/vscode-workspaces

docker start 132
vscode $WORKSPACES_DIR/ristretto_container.code-workspace

vscode $WORKSPACES_DIR/ristretto_local.code-workspace
