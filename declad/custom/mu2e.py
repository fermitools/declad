
import custom.metadata_converter 
import os
import sys
import hashlib

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

def rucio_dataset(desc, metadata, config):
    meta = metadata.copy()
    if "metadata" in metadata:
        meta.update(metadata["metadata"])
    if isinstance(meta.get("runs",[None])[0], list):
        # if it is sam style run list, get run number and type
        meta["run_number"] = meta["runs"][0][0]
        meta["run_type"] = meta["runs"][0][2]
    else:
        # if it is metacat style run list, get run number and type
        rl = meta.get("core.runs", meta.get("rs.runs", [0]))
        meta["run_number"] = rl[0]
        rt = meta.get("core.run_type", meta.get("dh.type", "mc"))
        meta["run_type"] = rt
    meta.update(template_tags(metadata))
    return config["rucio"]["dataset_did_template"] % meta

def metacat_dataset(desc, metadata, config):
    return config.get("metacat_dataset")

def template_tags(metadata):
    res = {}
    mhstr = hashlib.md5(metadata['name'].encode('utf-8')).hexdigest()
    shstr = hashlib.sha256(metadata['name'].encode('utf-8')).hexdigest()
    res["fo_md5hash"] = "%s/%s" % (mhstr[0:2], mhstr[2:4])
    res["fo_sha256hash"] = "%s/%s" % (shstr[0:2], shstr[2:4])
    if metadata["metadata"]["fn.owner"] == "mu2e":
         res["dirprefix"] =  "phy"
    else:
         res["dirprefix"] =  "usr" 
    return res

