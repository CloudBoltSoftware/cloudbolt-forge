#!/bin/bash -e

if [[ $1 ]]; then
    ip="$1"
else
    ip="10.70.70.10"
fi

echo "Adding server to monitoring system with ip $ip"

sleep 5

echo "success"
