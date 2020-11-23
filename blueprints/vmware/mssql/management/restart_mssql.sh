#!/usr/bin/env bash

echo "Restarting MSSql server..."
systemctl restart mssql-server

systemctl status mssql-server

echo "DONE!"
