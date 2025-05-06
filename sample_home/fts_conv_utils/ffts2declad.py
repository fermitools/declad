#!/usr/bin/python3

import argparse
import configparser
import yaml


class Converter:
    def __init__(self, ffts_file):
        self.config = configparser.ConfigParser(inline_comment_prefixes=('#',))
        self.config.read([ffts_file])

        self.filetypes = config.get("main", "filetypes").split(' ')

        self.scandirs = set()
        self.filepatterns = set()
        self.extractor_filepatterns = {}
        self.ftsfp = {}
        self.dest = {}
        self.constparts = {}
        self.mdparts = {}
        self.copy_commands = { 
         "xrdcp": 
           "xrdcp --cksum adler32:$adler32_checksum $src_url $dst_url",
         "gfal": 
           "gfal-copy --checksum adler32:$adler32_checksum $src_url $dst_url",
        }
        # these should come from... comand line options?
        self.copy_type = "xrdcp"
        self.exp = "hypot"
        self.drop_rse = "FNAL_SCRATCH"

    def cross_reference(self):
        for ft in self.filetypes:
            sect = f"filetype {ft}" 
            extractor = self.config[sect]["metadata-extracotor"]).strip()

            if not extractor in extractor_filepatterns:
                extractor_filepatterns[extractor] = set()
            self.ftsfp[ft] = set()

            for sd in self.config[sect]["scan-dirs"].strip.split(' '):
                 self.scandirs.add(sd)
      
            for fp in self.config[sect]["scan-file-patterns"]:
                 self.filepatterns.add(fp)
                 self.extractor_filepatterns[extractor].add(fp)
                 self.ftsfp[ft].add(fp)

            self.dest[ft] = [self.config[sect]["transfer-to"]]
            self.src[ft] = self.config[sect]["scan-dirs"].strip().split(' ')
            self.unify_dests()

    def common_prefix(self, dlist):
        firstcomps = []
        last_common_comp = 99
        for ft in self.filetypes:
            for d in dlist[ft]:
                comps = d.split('/')[1:]
                if not firstcomps:
                    firstcomps = comps
                for i in range(1,min(last_common_comp, len(comps)):
                    if comps[i] != firstcomps[i]:
                        last_common_comp = i
        last_common_comp += 1
        return '/' + '/'.join(firstcomps[:last_commmon_comp])
       

    def unify_dests(self):
        self.common_dest_prefix = self.common_prefix(self.dest)
        self.common_src_prefix = self.common_prefix(self.src)
         

     def write_metadata_extractor():
         mdout = "extractor.py"
         with open(mdout, "w") as mdefd:
             mdefd.write("from declad_utils import wildcard_to_regex, use_extractor\n")
             mdefd.write("import sys\n\n")
             mdefd.write("extre = {}\n")
             for mde in self.extractor_filepatterns:
                 fps = "['" + "', '".join(self.extractor_filepatterns[extractor]) + "']"
                 mdefd.write(f"extre['{mde}'] = wildcard_to_regex({fps}\n")
             mdefd.write("for fname in sys.argv:\n")
             mdefd.write("    for mde in extre:\n")
             mdefd.write("        m = extre[mde].match(fname)\n")
             mdefd.write("        if m:\n")
             mdefd.write("            use_extractor(mde, fname)\n")
             mdefd.write("            break\n")
             
     def write_custom_file():
         with open(cfout, "w") as cffd:
             cffd.write("from declad_utils import wildcard_to_regex")
             cffd.write("import sys\n\n")
             cffd.write("cfgre = {}\n")
             cffd.write("dstp = {}\n")
             for ft in self.ftsfp:
                 fts =  "['" + "', '".join(self.ftsfp[ft]) + "']"
                 cffd.write("cfgre['{ft}'] = wildcard_to_regex({fts})\n")
                 cffd.write("dstp['{ft}'] = {}\n")
             cffd.write("def template_tags(metadata):\n")
             cffd.write("    res = {}\n")
             cffd.write("    for ft in cfgre:\n")
             cffd.write("        m = cfgre[ft].match(metadata['name'])\n")
             cffd.write("        if m:\n")
             cffd.write("           res['pathmid'] = dstp[ft]\n")
             cffd.write("           break\n")
             cffd.write("    return res\n")
            
     def write_declad_cfg(dst_host ="destination_server"):
         cfg = {
           "debug_enabled": True,
           "default_category": "migrated",
           "destination_root_path": self.common_dest_prefix,
           "destination_server": f"fndcadoor.{self.local_domain}",
           "source_root_path": self.common_src_prefix,
           "source_server": "localhost",       # f-fts always is local
           "crate_dirs_command_template": ":", # assume auto-create
           "copy_command_template": self.copy_commands[self.copy_type],
           "download_command_template": "cp $src_path $dst_path",
           "delete_command_template": "rm $path",
           "quarantine_location": self.common_src_prefix + "/../quarantine",
           "metacat_namepsace": self.exp,
           "metacat_url": f:"https://metacat.{self.local_domain}:9443/{self.exp}_meta_prod/app",
           "rel_path_function": "template",
           "rel_path_pattern": f"%(custom_subdir)/{self.metadata_bits}",
           "log": "logs/declad.log",
           "rucio": {
              "activity": "Production",
              "dataset_did_template": "%(dataset_did)",
              "declare_to_rucio": True,
              "target_rses": []
              "drop_rse": self.drop_rse
           },
           "samweb": {
              "user": os.environ["USER"],
              "url": f"https://sam{self.exp}.{self.local_domain}:8483/sam/{self.exp}/api/",
              "cert": "certs/xxx-cert.pem",
              "key": "certs/xxx-key.pem",
           }
           "scanner": { 
               "type": "local",
               "replace_location": True,
               "path": self.common_src_prefix,
               "locaton": self.common_src_prefix,
               "ls_command_template": "find {self.alldirs} -type f -ls",
               "parse_re": "^(?P<type>[a-z-])\\S+\\s+\\d+\\s+\\d+\\s+\\d+\\s+(?P<size>\\d+)\\s+\\S.{11}\\s(?P<path>\\S+)$",
               "filename_patterns": list(self.filepatterns),
               "metadata_extractor": "declad_metadata_extractor.py",
               "metadata_extractor_log": "log/metadata_extractor.log",
           },
           "web_gui": {
               "prefix": "/declad",
               "site_title": "Declaration Daemon",
               "port": 8443,
            }
        }
        with os.open("declad.yaml", "w") as outf:
            outf.write(yaml.dump(cfg))
             

def main():
    aparser = argparse.ArgumentParser()
    aparser.add_argument('ffts_file')
    args = aparser.parse_args()

    cf = Converter(args.ffts_file)
    cf.cross_reference()
    cf.write_metadata_extractor()
    cf.write_declad_cfg()

if __name__ == '__main__':
   main()
