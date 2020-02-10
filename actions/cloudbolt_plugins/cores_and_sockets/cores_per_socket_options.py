"""
Display Cores per socket options based on CPU selection
"""

from functools import reduce


def factors(n):
    return set(reduce(list.__add__, ([i, n // i] for i in range(1, int(pow(n, 0.5) + 1)) if n % i == 0)))


def get_options_list(field, **kwargs):

    cpus = kwargs.get('control_value', None)

    if cpus:
        cpus = int(cpus)
        return list(factors(cpus))

    return None
