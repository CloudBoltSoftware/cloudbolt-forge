import subprocess


def run(job, logger=None):
    """
    Main entry point to run the Jupyterd start job
    """
    jupyterd_status = subprocess.call(["service", "jupyterd", "start"])
    if jupyterd_status == 0:
        job.progress('Jupyterd is now running')
        return "SUCCESS", "", "Jupyterd Started"
    else:
        job.progress('Jupyterd is not running')
        return "Failure", "", "Jupyterd could not be started"
