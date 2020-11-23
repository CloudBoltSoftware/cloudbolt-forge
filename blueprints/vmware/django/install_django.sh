#!/usr/bin/env bash

echo "Installing Django..."
pip3.6 install django

echo "Checking installed version..."
python3.6 -m django --version

echo "DONE!"
