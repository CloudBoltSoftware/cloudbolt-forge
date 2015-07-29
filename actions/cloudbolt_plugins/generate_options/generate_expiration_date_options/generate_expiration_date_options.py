import datetime

"""
CloudBolt Plug-in hook used as a sample to automatically generate options for
the expiration date parameter based on offsets from the current day
"""


def get_options_list(field, environment=None, group=None):
    six_months = datetime.datetime.now() + datetime.timedelta(days=180)
    one_month = datetime.datetime.now() + datetime.timedelta(days=30)
    one_week = datetime.datetime.now() + datetime.timedelta(days=7)

    if field.name not in ["expiration_date"]:
        return [None]

    return [("{:%m/%d/%Y}".format(one_week), "{:%m/%d/%Y} - One week from today".format(one_week)),
            ("{:%m/%d/%Y}".format(one_month), "{:%m/%d/%Y} - One month from today".format(one_month)),
            ("{:%m/%d/%Y}".format(six_months), "{:%m/%d/%Y} - Six months from today".format(six_months))]
