def get_options_list(field, control_value=None, control_value_dict=None, **kwargs):
    if not control_value_dict:
        return [
            ("", f"------ Please select a Monitoring Tool and Policy ------")
        ]
    monitoring_tool = control_value_dict.get("gpo_monitoring_tool", "")
    monitoring_policy = control_value_dict.get("gpo_monitoring_policy", "")
    if not monitoring_tool:
        return [("", f"------ Please select a Monitoring Tool ------")]
    if not monitoring_policy:
        return [("", f"------ Please select a Monitoring Policy ------")]
    # Add any logic to determine options based on the monitoring tool & policy.
    # Some trivial exmaple logic follows.
    options = [
        ("", f"------ Please select a Severity ------"),
        ("1", f"Severity 1 for {monitoring_tool} {monitoring_policy}"),
        ("2", f"Severity 2 for {monitoring_tool} {monitoring_policy}"),
    ]
    return options