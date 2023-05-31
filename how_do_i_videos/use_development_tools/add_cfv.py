from infrastructure.models import Server, CustomField


def run(**kwargs):
    server = Server.objects.get(id=22111)


def get_or_create_custom_field(name, label, description, cf_type, required=False):
    """
    Get or create a custom field with the given name, label, description, and type.
    """
    defaults = dict(
        label=label,
        description=description,
        type=cf_type,
        required=required,
    )

    cf, _ = CustomField.objects.get_or_create(
        name=name,
        defaults=defaults,
    )

    return cf