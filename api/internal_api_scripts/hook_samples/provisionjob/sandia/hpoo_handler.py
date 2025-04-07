import sys
import traceback
import re
import urllib
import urllib2
from urllib2 import HTTPError

# This HP OO wrapper relies on BeautifulSoup for XML Parsing
# (http://www.crummy.com/software/BeautifulSoup/download/3.x/)
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup


def run_hpoo_flow(
    oo_host,
    oo_flow,
    oo_params,
    oo_username,
    oo_password,
    oo_port="8443",
    oo_sync="execute",
):
    # input descriptions:
    # oo_host = ip/hostname of HP OO Central Server
    # oo_port = port number of HP OO Central Server
    # oo_flow = UUID or Path to flow in HP OO Central Repository
    # oo_params = hash of key:values to pass as paramaters to the flow
    # oo_username = HP OO Username
    # oo_password = HP OO Password
    # oo_sync = execute to run flow and wait for return, execute_async to run
    # flow and return immediately

    # url encode the params
    oo_params = urllib.urlencode(oo_params)

    # create the URL to execute the flow
    oo_url = "https://%s:%s/PAS/services/http/%s/%s?%s" % (
        oo_host,
        oo_port,
        oo_sync,
        oo_flow,
        oo_params,
    )

    # create a password manager for oo_url
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, oo_url, oo_username, oo_password)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)

    # load the page, executing the flow and retrieving the response
    try:
        pagehandle = urllib2.urlopen(oo_url)
        oo_response = pagehandle.readlines()
        oo_response = "".join(oo_response)
    except HTTPError as e:
        oo_response = """
<?xml version="1.0" encoding="UTF-8"?>
<executeResponse><executeReturn><run-id>None</run-id><run-report-url>None</run-report-url><display-run-report-url>None</display-run-report-url><run-start-time>None</run-start-time><run-end-time>None</run-end-time><run-history-id>None</run-history-id><flow-response>failure</flow-response><flow-result>{STDERR=%s;}</flow-result><flow-return-code>Error</flow-return-code></executeReturn></executeResponse>
""" % (
            e
        )

    return oo_url, oo_response


def build_dict_response(soup_response):
    # this will build a python dictionary storing the XML tags as key/value pairs

    dict_response = {}
    children = soup_response.findChildren(recursive=False)
    for tag in children:
        if tag.string:
            dict_response[tag.name] = tag.string
        else:
            dict_response[tag.name] = build_dict_response(tag)

    return dict_response


def parse_flow_results(flow_results):
    # used to parse the key/value pairs in the 'flow-results' XML response from HP OO
    # into a python dictionary

    # get rid of { and } from flow-result
    flow_results = flow_results[1:-1]

    # get a list of all key/value pairs stored in flow-result
    flow_outputs = re.compile("(\w+={1}.*?);", re.S).split(flow_results)

    # build a dictionary with all the key/value pairs stored in flow-result
    flow_output_dict = {}

    for flow_output in flow_outputs:
        if flow_output:
            # store the key/value in flow_output_dict, removing the trailing semicolon
            # from the value
            key, value = flow_output.split("=", 1)
            flow_output_dict[key] = value

    return flow_output_dict


def launch_hpoo_flow(
    oo_host,
    oo_flow,
    oo_params,
    oo_username,
    oo_password,
    oo_port="8443",
    oo_sync="execute",
):
    # wrapper function to collate all of the other functions in one area, returns the following:
    # oo_url: the URL that gets constructed to execute the flow
    # oo_response: the raw XML response from HP OO
    # soup_response: the BeautifulSoup object based on oo_response
    # dict_response: the python dictionary containing all of the flow XML elements in soup_response
    # flow_results: the python dictionary containing all of the flow output
    # variables in dict_response['executeresponse']['flow-result']

    oo_url, oo_response = run_hpoo_flow(
        oo_host, oo_flow, oo_params, oo_username, oo_password
    )
    soup_response = BeautifulStoneSoup(oo_response)
    dict_response = build_dict_response(soup_response)
    flow_results = parse_flow_results(
        dict_response["executeresponse"]["executereturn"]["flow-result"]
    )

    return oo_url, oo_response, soup_response, dict_response, flow_results


if __name__ == "__main__":
    # test harness:
    oo_host = "10.168.90.46"
    oo_flow = "007d1c3b-394f-4377-8e22-e85156d62be7"
    oo_params = {"vm_name": "HP OO 9.0"}
    oo_username = "admin"
    oo_password = "opsware"

    oo_url, oo_response, soup_response, dict_response, flow_results = launch_hpoo_flow(
        oo_host, oo_flow, oo_params, oo_username, oo_password,
    )
