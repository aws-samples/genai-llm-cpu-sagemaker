#!/bin/sh
echo "server.sh"
killall server
/app/server -m "$1" -c 2048 -t $(nproc --all) --host 0.0.0.0 --port 8081 & > /dev/null