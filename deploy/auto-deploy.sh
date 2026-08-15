#!/usr/bin/env bash
set -euo pipefail

repo=/opt/banana-mate
service=banana-mate.service
branch=main

cd "$repo"
current=$(sudo -u banana-mate git rev-parse HEAD)
sudo -u banana-mate git fetch --quiet origin "$branch"
target=$(sudo -u banana-mate git rev-parse "origin/$branch")

if [[ "$current" == "$target" ]]; then
    exit 0
fi

if [[ -n "$(sudo -u banana-mate git status --porcelain --untracked-files=no)" ]]; then
    echo "Tracked local changes found; refusing automatic deployment" >&2
    exit 1
fi

sudo -u banana-mate git merge --ff-only "origin/$branch"

if ! sudo -u banana-mate git diff --quiet "$current" "$target" -- requirements.txt; then
    "$repo/.venv/bin/pip" install -r requirements.txt
fi

systemctl restart "$service"
echo "Deployed ${target:0:7} and restarted $service"
