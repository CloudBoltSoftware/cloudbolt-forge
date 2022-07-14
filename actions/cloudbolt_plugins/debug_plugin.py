#!/usr/bin/env python

"""
To use this script to debug CB plug-ins:

 1. Install your favorite Python debugger. I recommend pudb: "pip install pudb"
 2. Tell Python what to do when it hits breakpoint()s: export PYTHONBREAKPOINT="pudb.set_trace"
 3. Execute your plug-in from the UI (e.g. by deploying the BP that contains it) to create a job record, then record
    that job ID (this must be the ID of the job that ran the plug-in, not a parent job deploy blueprint job)
 4. Add the line "breakpoint()" to your plug-in
 5. Place this script in /opt/cloudbolt
 6. Run it with `./debug_plugin.py -p <your plug-in ID> -j <your job ID>`
    When your breakpoint() is encountered, pudb should appear and allow you to inspect the state & step through.

Alternately, if you would like to have pudb rerun this program without ever quitting pudb, you can run it like this:
 6. `python -m pudb debug_plugin.py -p <your plug-in ID> -j <your job ID>`
 7. When run in this way, after your execution terminates, pudb will still be open. Press 'q', then choose 'Restart'

For more info:
 * see the pudb documentation: https://documen.tician.de/pudb/index.html
 * watch this 2 minute video demo: https://vimeo.com/729688724
"""
import threading
import click
import django


@click.command()
@click.option(
    "--plugin_id", "-p",
    required=True,
    type=int,
    help="The ID of the CB plugin to run",
)
@click.option(
    "--job_id", "-j",
    required=True,
    type=int,
    help="The ID of the job object from which to extract the inputs and context")
def main(plugin_id=None, job_id=None):
    # This conditional allows the debugger to re-run this script multiple times
    if not hasattr(django, 'apps'):
        # This is not done until main() is running so that it doesn't cause a slowdown each time they run this script
        # with the wrong arguments.
        django.setup()
        from cbhooks.models import CloudBoltHook
        from jobs.models import Job

    job = Job.objects.get(id=job_id)
    plugin = CloudBoltHook.objects.get(id=plugin_id)

    # The next 2 lines fool get_runtime_module() into thinking it's running in the context of a job thread, to cause it
    # to write the module file to the disk, instead of keeping it in memory where the debugger can't read it.
    thread = threading.current_thread()
    thread.job = job

    # Run the plug-in!
    plugin.run_without_retries(job=job)


if __name__ == "__main__":
    main()
