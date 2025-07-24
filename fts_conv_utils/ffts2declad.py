#!/usr/bin/python3

import argparse
import configparser
import os
import re
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
        self.ftscandirs = {}
        self.dest = {}
        self.src = {}
        self.alldirs = []
        self.constparts = {}
        self.mdparts = {}
        self.max_pos = 0
        self.pmap = {}

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
            self.untwist(extractor)

            if not extractor in self.extractor_filepatterns:
                self.extractor_filepatterns[extractor] = set()
            self.ftsfp[ft] = set()
            self.ftscandirs[ft] = set()

            for sd in self.config[sect].get("scan-dirs","").strip().split(" "):
                if sd:
                    self.scandirs.add(sd)
                    self.ftscandirs[ft].add(sd)

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

    def unify_path_components(self):
        # find the (sort-of) average position of various components
        # in the path
        for ft in self.filetypes:
            for d in self.dest.get(ft, []):
                # there are ${this/that} bits breaking the split on /
                d = re.sub(r"(\{[^}]*)/([^}]*\})",r"\1 div \2",d)
                comps = d.split("/")[1:]
                for i in range(len(comps)):
                    if i > self.max_pos:
                        self.max_pos = i
                    if not i in self.pmap:
                        self.pmap[i] = {}                  
                    if not comps[i] in self.pmap[i]:
                        self.pmap[i][comps[i]] = set()
                    self.pmap[i][comps[i]].add(ft)
        # debugging:
        #for i in range(self.max_pos+1):
        #    print(f"{i}:")
        #    for k in self.pmap[i]:
        #        pp = repr(self.pmap[i][k]).replace(',',',\n    ')
        #        print(f"  {k}:\n    {pp}")

    def unify_dests(self):
        self.common_src_prefix = self.common_prefix(self.src)
        self.unify_path_components()
        #print("common src prefix: ", self.common_src_prefix )

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
from declad_utils import wildcard_list_to_re, convert_fts
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

# Path Component Map
# ------------------
# path_comp_math[ position ][ value ] = pattern
# means that the position-th spot in the path will be (evaluated) value if our 
# source filepath / filename matches the pattern

path_comp_map = {}

""")
            for i in range(self.max_pos):
                cffd.write(f"path_comp_map[{i}] = {{}}\n")
                for comp in self.pmap[i]:
                    # build list of patterns for this component at this position
                    # we know the fileypes for this component at this position...
                    fpl = []
                    for ft in self.pmap[i][comp]:
                        if self.ftsfp[ft]:
                            fpl.extend(self.ftsfp[ft])
                        else:
                            fpl.extend(self.ftscandirs[ft])
                    fpl = sorted(fpl)
                    ffpl = "['" + "', '".join(fpl) + "']"
                    cffd.write(f"path_comp_map[{i}]['{comp}'] = wildcard_list_to_re({ffpl})\n")

            cffd.write("def template_tags(metadata):\n")
            cffd.write("    res = {}\n")
            cffd.write("    for i in path_comp_map:\n")
            cffd.write("        for comp in path_comp_map[i]:\n")
            cffd.write("            if path_comp_map[i][comp].match(metadata[name]):\n")
            cffd.write("                fcomp = convert_fts(comp, metadata)\n")
            cffd.write("                res[f'comp_{i}'] = comp\n")
            cffd.write("                break\n")
            cffd.write("    return res\n")

        os.system(f"black {cfout}||true")

    def write_declad_cfg(self,dst_host="destination_server"):
        cmppath = "/".join([ f"%(comp_{i})s" for i in range(self.max_pos)])
        cfg = {
            "debug_enabled": True,
            "default_category": "migrated",
            "destination_root_path": "/",
            "destination_server": f"fndcadoor.{self.local_domain}",
            "source_root_path": self.common_src_prefix,
            "source_server": "localhost",  # f-fts always is local
            "create_dirs_command_template": ":",  # assume auto-create
            "copy_command_template": self.copy_commands[self.copy_type],
            "download_command_template": "cp $src_path $dst_path",
            "delete_command_template": "rm $path",
            "quarantine_location": self.common_src_prefix + "/../quarantine",
            "metacat_namepsace": self.exp,
            "metacat_url": f"https://metacat.{self.local_domain}:9443/{self.exp}_meta_prod/app",
            "rel_path_function": "template",
            "rel_path_pattern": cmppath,
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

    def untwist(self, plugin_name):
        # the Plugins have evil twisted bits in them; prune those
        # out so they work as straight callable routines

        if not plugin_name:
            return

        plugin_dir = self.config["main"]["plugin-paths"]
        plugin_file = plugin_name.replace("-","_") + "_metadata.py"
        if os.path.exists(f"plugins/{plugin_file}"):
            # already did this one
            return
        with open(f"{plugin_dir}/{plugin_file}", "r") as fin:
             with open(f"plugins/{plugin_file}", "w") as fout:
                 for line in fin.readlines():
                     if re.match("(from.*twist.*import)|( *@defer\\.)", line):
                          continue
                     line = re.sub("= *yield ", "= ", line)
                     line = re.sub("defer.returnValue\((.*)\)", "return \\1", line)
                     line = re.sub("^[a-zA-Z]*Extractor = ", "extractor = ", line)
                     line = re.sub("\\.iteritems\\(", ".items(", line)
                     line = re.sub("yield threads.deferToThread", "threads.deferToThread", line)
                     line = re.sub("threads.deferToThread\\(([^,]*),*(.*)\\)", "\\1(\\2)", line)
                     fout.write(line)


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
