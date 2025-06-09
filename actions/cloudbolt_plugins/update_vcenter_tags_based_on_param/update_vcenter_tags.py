"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import (
            tokenize_template_string,
            generate_string_from_template,
            set_progress,
        )
from utilities.logger import ThreadLogger
from infrastructure.models import Server
from resourcehandlers.vmware import vapi_wrapper as v

logger = ThreadLogger(__name__)

def run(job, *args, **kwargs):
    set_progress("This will show up in the job details page in the CB UI, and in the job log")

    #grab server
    server_hostname = kwargs.get('server')
    server = Server.objects.filter(hostname=server_hostname).last()
    logger.info(f"server: {server}")

    #get moid
    moid = server.vmwareserverinfo.moid

    # get rh technology
    rh = server.resource_handler.cast()

    # get api wrapper
    w = rh.get_api_wrapper()

    # get vapi wrapper
    v = w.get_vapi_wrapper()

    #get tag value
    tag_value = server.vmwareserverinfo.tags()['mw-env']
    logger.info(f"tag={tag_value}")

    #run conditionals
    if tag_value == "Production":
        v.update_vm_tags_in_vcenter(moid, {'mw-new': 'Backup'})
        rh.update_tags(server)
        logger.info("ran production line") # link server with backup tag
    elif tag_value == "test":
        v.update_vm_tags_in_vcenter(moid, {'mw-new': 'svr_test'})
        rh.update_tags(server)
        logger.info("ran svr_test line") # link with srv tag
    else:
        logger.info("tag not found")


    # Example of how to fetch arguments passed to this plug-in ('server' will be available in
    # some cases)
    if server:
        set_progress("This plug-in is running for server {}".format(server))

    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))

    if True:
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "Sample output message", "Sample error message, this is shown in red"