# Add Python code
from common.methods import set_progress
"""
Sample for appending any-any edge firewall rule with HTTP and HTTPS
"""

def run(job, service=None, **kwargs):
    # Get the resource handler from the network environment
    network = service.servicenetwork_set.first()
    environment = network.environment
    vcenter = environment.resource_handler.cast()

    # Get firewall config for service edge device
    firewall_url = "api/4.0/edges/{}/firewall/config".format(network.appliance_identifier)
    nsx_api_wrapper = vcenter.nsx_endpoint_api_wrapper()

    # Generate firewall rules
    rules_xml = "<firewallRules>"
    rules_xml += """
        <firewallRule>
          <name>Web</name>
          <ruleType>user</ruleType>
          <enabled>true</enabled>
          <description>Web any-any rule</description>
          <action>accept</action>
          <source>
            <exclude>false</exclude>
            <vnicGroupId>external</vnicGroupId>
          </source>
          <destination>
            <exclude>false</exclude>
            <vnicGroupId>vse</vnicGroupId>
          </destination>
          <application>
            <applicationId>application-77</applicationId>
            <applicationId>application-239</applicationId>
          </application>
        </firewallRule>
    """
    rules_xml += "</firewallRules>"

    # Push firewall rules
    nsx_api_wrapper.request("POST", firewall_url + '/rules', rules_xml, "text/xml")
    xml = nsx_api_wrapper.get(firewall_url)
    set_progress(xml)

    return 'SUCCESS', '', ''
