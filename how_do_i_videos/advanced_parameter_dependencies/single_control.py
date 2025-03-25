def get_options_list(field, control_value=None, **kwargs):
    """
    A plug-in for regenerating 'Species' options based on the value of the controlling field 'Genus'
    field: This is the dependent field.
    control_value: The value entered on the form for the control field. This value determines what will be displayed in "field"
    """
    options = []

    if control_value == '1':
        options = [
            ("", "----- Select a Value -----"),
            ("A", "Value A"),
            ("B", "Value B"),
            ("C", "Value C")
        ]
    elif control_value == '2':
        options = [
            ("", "----- Select a Value -----"),
            ("D", "Value D"),
            ("E", "Value E"),
            ("F", "Value F")
        ]
    elif control_value == '3':
        options = [
            ("", "----- Select a Value -----"),
            ("G", "Value G"),
            ("H", "Value H"),
            ("I", "Value I")
        ]
    return options