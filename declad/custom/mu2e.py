
import custom.metadata_converter 
import os
import sys

mc = metadata_converter.MetadataConverter("mu2e")

def metacat_metadata(desc, metadata, config):
    if ("size" in metadata and "metadata" in metadata):
        # already is metacat metadata, just return the metadata part
        return metadata["metadata"]
    
    namespace = config.get("metacat_namespace")
    res = mc.convert_all_sam_mc(metadata, namespace)  
    return res["metadata"]

def sam_metadata(desc, metadata, config):
    if ("metadata" in metadata):
        # is new style metadata..
        out = mc.convert_all_mc_sam(metadata)
    else:
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

def get_file_scope(desc, metadata, config):
    #return metadata["runs"][0][2]
    return "mu2epro"

def get_dataset_scope(desc, metadata, config):
    return get_file_scope(desc, metadata, config)

def metacat_dataset(desc, metadata, config):
    return config.get("metacat_dataset")

