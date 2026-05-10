#!/bin/bash
echo "Starting Advanced Chaos Monkey for Linux..."

while true; do
    sleep $((30 + RANDOM % 60))
    action=$((RANDOM % 3))
    case $action in
        0)
            echo "Chaos: Simulating Network Drop"
            nmcli networking off
            sleep 10
            nmcli networking on
            ;;
        1)
            echo "Chaos: Clipboard Wipe"
            xsel -bc || xclip -selection clipboard /dev/null
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
