from common.methods import set_progress


def get_options_list(field, **kwargs):
    env = kwargs.get("environment")
    options = []
    networks = list(env.networks().keys())
    for network in networks:
        option = (network.network, network.name)
        if option not in options:
            options.append(option)
    return {
        'options': options,
    }
