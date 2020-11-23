#!/usr/bin/env bash

# Stop mysqld
echo "Stopping Mysql"

/etc/init.d/mysqld stop

if [ $? -eq 0 ]; then
    echo "Successfully Stopped."
else
    echo "Failed Stopping Mysql"
fi

echo "DONE"
