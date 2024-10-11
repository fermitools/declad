import yaml
import sys

class Config(dict):
    _valid_keys = set( [
        "copy_command_template",
        "create_dirs_command_template",
        "debug_enabled",
        "default_category",
        "delete_command_template",
        "destination_root_path",
        "destination_server",
        "download_command_template",
        "graphite.host",
        "graphite.interval",
        "graphite.port",
        "graphite.namespace",
        "graphite.bin",
        "keep_interval",
        "log",
        "low_water_mark",
        "meta_suffix",
        "metacat_dataset",
        "metacat_namespace",
        "metacat_url",
        "max_movers",
        "quarantine_location",
        "rel_path_function",
        "rel_path_pattern",
        "retry_cooldown",
        "rucio.activity",
        "rucio.dataset_did_template",
        "rucio.declare_to_rucio",
        "rucio.target_rses",
        "rucio.drop_rse",
        "sam_location_template",
        "samweb.user",
        "samweb.url",
        "samweb.token",
        "samweb.cert",
        "samweb.key",
        "scanner.type",
        "scanner.replace_location",
        "scanner.path",
        "scanner.interval",
        "scanner.location",
        "scanner.ls_command_template",
        "scanner.metadata_extractor_log",
        "scanner.metadata_extractor",
        "scanner.parse_re",
        "scanner.filename_patterns",
        "scanner.filename_pattern",
        "scanner.server",
        "scanner.timeout",
        "source_root_path",
        "source_server",
        "transfer_timeout",
        "web_gui.prefix",
        "web_gui.site_title",
        "web_gui.port",
    ])

    def __init__(self, config_file):
        with open(config_file, "r") as cff:
            cfg = yaml.load(cff , Loader=yaml.SafeLoader)
        self.check(cfg)
        dict.__init__(self, cfg.items())

    def check(self, cfg ):
        unknown_keys= set()
        for k,v in cfg.items():
            if isinstance(v,dict):
                for k2, v2 in v.items():
                    if not f"{k}.{k2}" in Config._valid_keys:
                        unknown_keys.add( f"{k}.{k2}" )
            else:
                if not k in Config._valid_keys:
                    unknown_keys.add( k )
        if unknown_keys:
           raise KeyError(f"Unknown keys: {','.join(unknown_keys)} in config")
           

if __name__ == "__main__":
     # run as config file checker...
     cf = Config(sys.argv[1])
