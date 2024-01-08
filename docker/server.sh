#!/bin/sh
echo "server.sh"
echo "args: $1"

# Check if NVIDIA GPU is available
if lspci | grep -i nvidia &> /dev/null; then
  echo "NVIDIA GPU is available."
  NGL=999
  CPU_PER_SLOT=1
else
  echo "No NVIDIA GPU found."
  NGL=0
  CPU_PER_SLOT=4
fi

killall server
/app/server -m "$1" -c 2048 -t $(nproc --all) --host 0.0.0.0 --port 8081 -cb -np $(($(nproc --all) / $CPU_PER_SLOT)) -ngl $NGL &