from common.methods import set_progress
import requests
import rh
import json
from utilities.logger import ThreadLogger
logger = ThreadLogger(__name__)

s=requests.Session()
s.verify=False
vcip=""
username=""
password=""
cookie=""
def get_vc_session(username,password):
        global cookie
        s.post('https://'+vcip+'/rest/com/vmware/cis/session', auth=(username,password))
        cookie = s.cookies['vmware-api-session-id']
        return s
def run(job, *args, **kwargs):
    set_progress("This will show up in the job details page in the CB UI, and in the job log")
    
    # Example of how to fetch arguments passed to this plug-in ('server' will be available in
    # some cases)
    global vcip
    global username
    global password
    server = kwargs.get('server')
    rh = server.resource_handler.cast()
    moid =  server.vmwareserverinfo.moid
    vcip = rh.ip
    username=rh.serviceaccount
    password = rh.servicepasswd
    get_vc_session(username,password)
    headers = {
    'Content-Type': "application/json",
    'vmware-api-session-id': cookie
    }
    url='https://'+vcip+'/rest/vcenter/vm/'+moid+'/power/reset'
    r = requests.post(url, headers = headers, verify = False)
    if r.status_code == 200:
        logger.info(f"Reset request got successful on {server}")
    else:
        logger.info(f"Reset request got failed on {server}")
        r.raise_for_status()
    if server:
        set_progress("This plug-in is ran for server {}".format(server))

    set_progress("Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items()))

    if True:
        return "SUCCESS", "Sample output message", ""
    else:
        return "FAILURE", "Sample output message", "Sample error message, this is shown in red"
