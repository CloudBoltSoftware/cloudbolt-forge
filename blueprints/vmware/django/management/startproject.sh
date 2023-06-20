#!/usr/bin/env bash

echo "Creating a project..."
django-admin startproject "{{ project_name }}"

if [ $? -eq 0 ]; then
    echo "Project created successfully"

fi
echo "Done"
