#!/usr/bin/env python

"""
An example for creating plug-ins that regenerate field options for a dependent
parameter based on choices made in previous parameter fields.

The following example is to set monitoring values, depending on the chosen
monitoring plaftorm.

Feel free to edit it to fulfill your needs.

To make a parameter dependent on another:
    - click on parameter name, e.g. Mode
    - under dependencies, click on pencil next to 'This parameter is not dependent on any other parameters'
    - for Controlling Field, select controlling parameter, e.g. Monitoring Tool
    - for Dependency Type, select Regenerate Options
    - click Next
"""


"""Create Action Inputs for desired form fields"""
Monitoring_Tool = {{ monitoring_tool }}
Mode = {{ mode }}


def generate_options_for_monitoring_tool(server=None, **kwargs):
    """
    Define a list of tuples that will be returned to generate the field options
    for the Monitoring_Tool Action Input.

    In this example Mode is dependent on Monitoring_Tool. Dependencies between
    parameters can be defined within the dependent parameter's page.

    each tuple follows this order: (value, label)

    where value is the value of the choice, and label is the label that appears
    in the field.
    """
    options = [('nagios', 'Nagios'),
               ('zabbix', 'Zabbix')
               ]
    return options


def generate_options_for_mode(server=None, control_value=None, **kwargs):
    """
    Define a list of tuples that will be returned to generate the field options
    for the Mode Action Input, depending on the value from Monitoring_Tool
    passed in as the control_value argument.

    each tuple follows this order: (value, label)

    where value is the value of the choice, and label is the label that appears
    in the field.
    """
    if control_value == 'nagios':
        return [('log', 'Log'), ('network', 'Network'), ('server', 'Server')]
    elif control_value == 'zabbix':
        return [('network', 'Network'), ('server', 'Server'),
                ('service', 'Service'), ('cloud', 'Cloud'),
                ('databases', 'Databases'), ('storage', 'Storage')
                ]
