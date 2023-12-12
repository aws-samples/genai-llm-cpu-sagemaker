#!/bin/sh
echo "server.sh"

# Check if NVIDIA GPU is available
if lspci | grep -i nvidia &> /dev/null; then
  echo "NVIDIA GPU is available."
  NGL=999
else
  echo "No NVIDIA GPU found."
  NGL=0
fi

killall server
/app/server -m "$1" -c 2048 -t $(nproc --all) --host 0.0.0.0 --port 8081 -np $(($(nproc --all) / 4)) -ngl $NGL & > /dev/null