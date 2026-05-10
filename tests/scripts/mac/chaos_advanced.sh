#!/bin/bash
echo "Starting Advanced Chaos Monkey for macOS..."

while true; do
    sleep $((30 + RANDOM % 60))
    action=$((RANDOM % 3))
    case $action in
        0)
            echo "Chaos: Simulating Network Drop"
            # macOS simple network drop via networksetup
            networksetup -setnetworkserviceenabled Wi-Fi off
            sleep 10
            networksetup -setnetworkserviceenabled Wi-Fi on
            ;;
        1)
            echo "Chaos: Clipboard Wipe"
            echo -n | pbcopy
            ;;
        2)
            echo "Chaos: CPU Spike"
            yes > /dev/null &
            PID=$!
            sleep 15
            kill -9 $PID
            ;;
    esac
done
