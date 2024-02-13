"""
eb-remote-bp-action-shared MODIFIED
"""
from common.methods import set_progress


def run(job, *args, **kwargs):
    set_progress("This will show up in the job details page in the CB UI, and in the job log")

    # Example of how to fetch arguments passed to this plug-in ('server' will be available in
    # some cases)
    server = kwargs.get('server')
    if server:
        set_progress("This plug-in is running for server {}".format(server))

    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))

    if True:
        # Each of these keys in the return dictionary is optional (if status is not included, it'll be treated as "SUCCESS")
        return {"status": "SUCCESS", "output_message": "Sample output message"}
    else:
        return {"status": "FAILURE", "output_message": "Sample output message", "error_message": "Sample error message, this is shown in red"}
