#!/usr/bin/env bash

# Restart mysqld
echo "Restarting Mysql"

/etc/init.d/mysqld restart

if [ $? -eq 0 ]; then
    echo "Successfully Restarted."
else
    echo "Failed Restarting Mysql"
fi

echo "DONE"
