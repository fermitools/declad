
mc = metadata_converter.MetadataConverter("dune")

def new_metacat_metadata(desc, metadata, config):
    # just use the metadata_converter
    if ("size" in metadata and "metadata" in metadata):
        # already is metacat metadata, just return the metadata part
        return metadata["metadata"]
    
    namespace = "dune"
    res = mc.convert_all_sam_mc(metadata, namespace)  
    return res["metadata"]

CoreAttributes = {
    "start_time":   "core.start_time",
    "end_time":     "core.end_time",
    "event_count":  "core.event_count",
    "file_type":    "core.file_type", 
    "file_format":  "core.file_format",
    "data_tier":    "core.data_tier", 
    "data_stream":  "core.data_stream", 
    "events":       "core.events",
    "first_event":  "core.first_event_number",
    "last_event":   "core.last_event_number",
    "event_count":  "core.event_count",
    "group":        "core.group",
    "lum_block_ranges":        "core.lum_block_ranges"
}

def metacat_metadata(desc, metadata, config):

    if ("size" in metadata and "metadata" in metadata):
        # already is metacat metadata, just return the metadata part
        return metadata["metadata"]
    
    metadata = metadata.copy()      # so that we do not modify the input dictionary in place
    
    #
    # discard native file attributes
    #
    metadata.pop("file_size", None)
    metadata.pop("checksum", None)
    metadata.pop("file_name", None)
    metadata.pop("creator", None)           # ignored
    metadata.pop("user", None)              # ignored

    out = {}
    #
    # pop out and convert core attributes
    #
    runs_subruns = set()
    run_type = None
    runs = set()
    for run, subrun, rtype in metadata.pop("runs", []):
        run_type = rtype
        runs.add(run)
        runs_subruns.add(100000*run + subrun)
    out["core.runs_subruns"] = sorted(list(runs_subruns))
    out["core.runs"] = sorted(list(runs))
    out["core.run_type"] = run_type
    app = metadata.pop("application", None)
    if app:
        if "name" in app:               out["core.application.name"]    = app["name"]
        if "version" in app:            out["core.application.version"] = app["version"]
        if "family" in app:             out["core.application.family"]  = app["family"]
        if "family" in app and "name" in app:
            out["core.application"] = app["family"] + "." + app["name"]
    
    for k in ("start_time", "end_time"):
        t = metadata.pop(k, None)
        if t is not None:
            if isinstance(t, str):
                t = datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp()
            elif not isinstance(t, (int, float)):
                raise ValueError("Unsupported value for %s: %s (%s)" % (k, t, type(t)))
            out["core."+k] = t
    #
    # The rest must be either dimensions or known core attributes
    #
    
    for name, value in metadata.items():
        if '.' not in name:
            if name in CoreAttributes:
                name = CoreAttributes[name]
            elif DefaultCategory is None:
                raise ValueError("Unknown core metadata parameter: %s = %s for file %s" % (name, value, desc.Name))
            else:
                name = config.get("default_category") + "." + name
        if config.get("lowercase_meta_names", False):
            name = name.lower()
        out[name] = value
    
    out.setdefault("core.event_count", len(out.get("core.events", [])))
    return out

def sam_metadata(desc, metadata, config):
    if ("metadata" in metadata):
        # is new style metadata..
        out = mc.convert_all_mc_sam(metadata)
    else:
        out = metadata.copy()
    out = metadata.copy()
    out["file_name"] = desc.Name
    out["user"] = config.get("samweb", {}).get("user", os.getlogin())
    ck = out.get("checksum")

    # take either "checksum" : [ "adler32:xxx" ] or "checksum": "adler32:xxx" 
    if isisntance(ck, list):
        ck = list[0]

    if ck:
        if ':' in ck:
            type, value = ck.split(':', 1)
        else:
            type, value = "adler32", ck
    out["checksum"] = [f"{type}:{value}"]
    if "metadata" in out:
        for k,v in core_attributes:
            if out["metadata"].get(v):
                out[k] = out["metadata"].get(v)
        out["file_size"] = out["size"]
        out.pop("size")
        out.pop("metadata")
        out.pop("checksums")
    out.pop("events", None)
    #print("sam_metadata:"), pprint.pprint(out)
    return out

def get_file_scope(desc, metadata, config):
    return metadata["runs"][0][2]

def get_dataset_scope(desc, metadata, config):
    return get_file_scope(desc, metadata, config)

def metacat_dataset(desc, metadata, config):
    return config["metacat_dataset"]

