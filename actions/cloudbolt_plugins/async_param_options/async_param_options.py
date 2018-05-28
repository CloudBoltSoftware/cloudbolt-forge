import sqlite3
from common.methods import set_progress


def suggest_options(field, query, **kwargs):
    """
    Sample plugin that enables CloudBolt interface to provide a form field that
    autocompletes as the user is typing, but that fetches matching options by
    invoking this action asynchronously.  Use this if the set of options is so
    large that the normal `get_options_list` (which renders all options into
    the page) performs poorly.

    Note: This is just an example of one way such an action might be used, by
    querying a local SQLite database. It could also fetch options from an
    external API.

    Args:
        query: the word the user has typed 

    Returns:
        list of tuples representing dropdown options ("value", "Visible label")]
    """

    # Limit the results to something reasonable, for a responsive user experience;
    # this action is called as the user is typing and results should be returned
    # as quickly as possible, but also not too many.
    max_results = 50

    # Query an SQLite database table for matching email addresses.
    conn = sqlite3.connect('/var/opt/cloudbolt/proserv/ldap_users.db')
    c = conn.cursor()
    emails = c.execute(
        'SELECT email FROM users WHERE email LIKE ? ORDER BY email LIMIT ?',
        ('%{}%'.format(query), max_results)
    )
    
    # Use the SQLite query result here, before closing the DB connection. It
    # materializes the cursor and avoids Python exception.
    options = [(email, email) for email in emails]
        
    conn.close()
    return options


def get_options_list(*args, **kwargs):
    """
    This function, though not used, must be present in any "Generated Parameter
    Options" action.  It will be ignored as long as `suggest_options` is
    present.
    """
    return None
