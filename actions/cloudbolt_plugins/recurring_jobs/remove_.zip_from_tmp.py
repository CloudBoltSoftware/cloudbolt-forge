"""
This action removes all the zip files from CloudBolt /tmp/systemd-private* directory.
"""
from common.methods import set_progress
import glob
import os
import time

def run(job, *args, **kwargs):
    zip_file_list = glob.glob("/tmp/systemd-private*/tmp/*.zip")
    set_progress("Found following zip files in /tmp/systemd/*/tmp: {}".format(zip_file_list))
    for file in zip_file_list:
        #Only remove zip files that are at least 5 minutes old.
        if os.path.getmtime(file) < time.time() - 5 * 60:
            set_progress("Removing these files {}".format(file))
            os.remove(file)

    return "SUCCESS", "", ""

