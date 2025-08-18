#!/bin/bash

puppet agent --test

rc=$?
echo "\`puppet agent --test\` exited with code $rc"

if [ $rc -eq 2 ] ; then
    echo Puppet status changed
else
    exit $rc
fi
