#!/usr/bin/env bash

ssh -o StrictHostKeyChecking=no -i "$PEM_FILE" "$SSH_USER" bash <<EOF
cd "/root/x-twitter-thread-dump"

git fetch --all
git reset --hard origin/main

/root/.local/bin/uv sync --extra server

cp misc/nginx.conf /etc/nginx/nginx.conf
cp misc/x-twitter-thread-dump-api.service /etc/systemd/system/x-twitter-thread-dump-api.service

systemctl daemon-reload
service x-twitter-thread-dump-api restart

EOF
