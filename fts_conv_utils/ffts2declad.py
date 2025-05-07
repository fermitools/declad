#!/usr/bin/python3

import argparse
import configparser
import os
import socket
import yaml

class Converter:
    def __init__(self, ffts_file):
        self.config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self.config.read([ffts_file])

        self.filetypes = self.config.get("main", "filetypes").split(" ")

        self.scandirs = set()
        self.filepatterns = set()
        self.extractor_filepatterns = {}
        self.ftsfp = {}
        self.dest = {}
        self.src = {}
        self.alldirs = []
        self.constparts = {}
        self.mdparts = {}

        self.local_domain = socket.getfqdn()
        firstdot = self.local_domain.index(".")
        self.local_domain = self.local_domain[firstdot:]

        self.copy_commands = {
            "xrdcp": "xrdcp --cksum adler32:$adler32_checksum $src_url $dst_url",
            "gfal": "gfal-copy --checksum adler32:$adler32_checksum $src_url $dst_url",
        }
        # these should come from... comand line options?
        self.copy_type = "xrdcp"
        self.exp = "hypot"
        self.drop_rse = "FNAL_SCRATCH"

    def cross_reference(self):
        for ft in self.filetypes:
            sect = f"filetype {ft}"
            extractor = self.config[sect].get("metadata-extractor","").strip()

            if not extractor in self.extractor_filepatterns:
                self.extractor_filepatterns[extractor] = set()
            self.ftsfp[ft] = set()

            for sd in self.config[sect].get("scan-dirs","").strip().split(" "):
                if sd:
                    self.scandirs.add(sd)

            for fp in self.config[sect].get("scan-file-patterns","").strip().split(" "):
                if fp:
                    self.filepatterns.add(fp)
                    self.extractor_filepatterns[extractor].add(fp)
                    self.ftsfp[ft].add(fp)

            self.dest[ft] = self.config[sect].get("transfer-to","").split(" ")
            self.src[ft] = self.config[sect].get("scan-dirs", "").strip().split(" ")
            self.alldirs.extend(self.src[ft])
        self.unify_dests()
        self.alldirs = set([ x.replace(self.common_src_prefix+'/','') for x in self.alldirs])

    def common_prefix(self, dlist):
        firstcomps = []
        last_common_comp = 99
        for ft in self.filetypes:
            for d in dlist.get(ft, []):
                comps = d.split("/")[1:]
                if not firstcomps:
                    firstcomps = comps
                for i in range(1, min(last_common_comp, len(comps),len(firstcomps))):
                    if comps[i] != firstcomps[i]:
                        last_common_comp = i

        last_common_comp += 1
        return "/" + "/".join(firstcomps[:last_common_comp])

    def unify_dests(self):
        self.common_dest_prefix = self.common_prefix(self.dest)
        self.common_src_prefix = self.common_prefix(self.src)
        print("common src prefix: ", self.common_src_prefix )
        print("common dest prefix: ", self.common_dest_prefix )

    def write_metadata_extractor(self):
        mdout = "extractor.py"
        with open(mdout, "w") as mdefd:
            mdefd.write("from declad_utils import wildcard_list_to_re, use_extractor\n")
            mdefd.write("import sys\n\n")
            mdefd.write("extre = {}\n")

            for mde in self.extractor_filepatterns:
                if mde:
                    expats = sorted(list(self.extractor_filepatterns[mde]))
                    fps = "['" + "', '".join(expats)+ "']"
                    mdefd.write(f"extre['{mde}'] = wildcard_list_to_re({fps})\n")
            mdefd.write("for fname in sys.argv:\n")
            mdefd.write("    for mde in extre:\n")
            mdefd.write("        if extre[mde].match(fname):\n")
            mdefd.write("            use_extractor(mde, fname)\n")
            mdefd.write("            break\n")
        os.system(f"black {mdout}||true")

    def write_custom_file(self):
        cfout = "custom.py"
        with open(cfout, "w") as cffd:

            cffd.write("""
from declad_utils import wildcard_list_to_re
import sys
extre = {}

import custom.metadata_converter 
import os
import sys
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
    return metadata["creator"]

def get_dataset_scope(desc, metadata, config):
    return get_file_scope(desc, metadata, config)

def metacat_dataset(desc, metadata, config):
    return config.get("metacat_dataset")

cfgre = {}
dstp = {}

""")
            for ft in self.ftsfp:
                fpl = sorted(list(self.ftsfp[ft]))
                fts = "['" + "', '".join(fpl) + "']"
                cffd.write(f"cfgre['{ft}'] = wildcard_list_to_re({fts})\n")
                cffd.write(f"dstp['{ft}'] = {self.dest[ft]}\n")

            cffd.write("def template_tags(metadata):\n")
            cffd.write("    res = {}\n")
            cffd.write("    for ft in cfgre:\n")
            cffd.write("        if cfgre[ft].match(metadata['name']):\n")
            cffd.write("           res['pathmid'] = dstp[ft]\n")
            cffd.write("           break\n")
            cffd.write("    return res\n")

        os.system(f"black {cfout}||true")

    def write_declad_cfg(self,dst_host="destination_server"):
        cfg = {
            "debug_enabled": True,
            "default_category": "migrated",
            "destination_root_path": self.common_dest_prefix,
            "destination_server": f"fndcadoor.{self.local_domain}",
            "source_root_path": self.common_src_prefix,
            "source_server": "localhost",  # f-fts always is local
            "crate_dirs_command_template": ":",  # assume auto-create
            "copy_command_template": self.copy_commands[self.copy_type],
            "download_command_template": "cp $src_path $dst_path",
            "delete_command_template": "rm $path",
            "quarantine_location": self.common_src_prefix + "/../quarantine",
            "metacat_namepsace": self.exp,
            "metacat_url": f"https://metacat.{self.local_domain}:9443/{self.exp}_meta_prod/app",
            "rel_path_function": "template",
            "rel_path_pattern": f"%(custom_subdir)",
            "log": "logs/declad.log",
            "rucio": {
                "activity": "Production",
                "dataset_did_template": "%(dataset_did)",
                "declare_to_rucio": True,
                "target_rses": [],
                "drop_rse": self.drop_rse,
            },
            "samweb": {
                "user": os.environ["USER"],
                "url": f"https://sam{self.exp}.{self.local_domain}:8483/sam/{self.exp}/api/",
                "cert": "certs/xxx-cert.pem",
                "key": "certs/xxx-key.pem",
            },
            "scanner": {
                "type": "local",
                "replace_location": True,
                "path": self.common_src_prefix,
                "locaton": self.common_src_prefix,
                "ls_command_template": f"find {' '.join(self.alldirs)} -type f -ls",
                "parse_re": "^(?P<type>[a-z-])\\S+\\s+\\d+\\s+\\d+\\s+\\d+\\s+(?P<size>\\d+)\\s+\\S.{11}\\s(?P<path>\\S+)$",
                "filename_patterns": list(self.filepatterns),
                "metadata_extractor": "declad_metadata_extractor.py",
                "metadata_extractor_log": "log/metadata_extractor.log",
            },
            "web_gui": {
                "prefix": "/declad",
                "site_title": "Declaration Daemon",
                "port": 8443,
            },
        }
        with open("declad.yaml", "w") as outf:
            outf.write(yaml.dump(cfg))


def main():
    aparser = argparse.ArgumentParser()
    aparser.add_argument("ffts_file")
    args = aparser.parse_args()

    cf = Converter(args.ffts_file)
    cf.cross_reference()
    cf.write_metadata_extractor()
    cf.write_declad_cfg()
    cf.write_custom_file()


if __name__ == "__main__":
    main()
