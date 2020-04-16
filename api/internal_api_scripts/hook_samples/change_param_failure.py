from jobs.models import CFVChangeParameters


def run(job, logger=None):
    jp = job.job_parameters.cast()
    if not isinstance(jp, CFVChangeParameters):
        return (
            "FAILURE",
            "This sample hook should be used only to test change params on servers",
            "This sample hook should be used only to test change params on servers",
        )
    job.set_progress(
        "Called FAILURE param change hook on server: {}".format(jp.instance)
    )
    job.set_progress(
        "   Old value: {} -->  New value: {}".format(
            jp.pre_custom_field_value, jp.post_custom_field_value
        )
    )
    return "FAILURE", "Failed on purpose", "Failed on purpose"
