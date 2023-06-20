#!/usr/bin/env bash

echo "Stopping MSSql server..."
systemctl stop mssql-server

systemctl status mssql-server

echo "DONE!"
