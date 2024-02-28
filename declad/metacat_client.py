from metacat.webapi import MetaCatClient
from metacat.webapi.webapi import AlreadyExistsError

def client(config):
    if "metacat_url" in config:
        return MetaCatClient(config.get("metacat_url"))
    else:
        return None
