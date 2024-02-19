
import metadata_converter 

mc = metadata_converter.MetadataConverter("mu2e")

def metacat_metadata(desc, metadata, config):
    return mc.convert_all_sam_mc(metadata)  

def sam_metadata(desc, metadata, config):
    out = metadata.copy()
    out["file_name"] = desc.Name
    out["user"] = config.get("samweb", {}).get("user", os.getlogin())
    ck = out.get("checksum")
    # deal with checksum : "value" vs checksum: "adler32:value" vs checksum: ["adler32:value"]
    if ck and not isinstance(ck, list):
        if ':' in ck:
            type, value = ck.split(':', 1)
        else:
            type, value = "adler32", ck
    out["checksum"] = [f"{type}:{value}"]
    out.pop("events", None)
    #print("sam_metadata:"), pprint.pprint(out)
    return out

def file_scope(desc, metadata, config):
    return metadata["runs"][0][2]

def dataset_scope(desc, metadata, config):
    return file_scope(desc, metadata, config)

def metacat_dataset(desc, metadata, config):
    return config["metacat_dataset"]

