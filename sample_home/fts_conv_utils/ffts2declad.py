#!/usr/bin/python3

import argparse
import configparser


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

            self.dest[ft] = self.config[sect]["transfer-to"]
            self.unify_dests()


    def unify_dests(self):
        # go thorough filetype destinations, come up with 3 parts
        # * common prefix (i.e. /pnfs/nova/production/
        # * hardcoded parts per filetype
        # * metadata parts per filetype
        # then try to unify path components
        firstcomps = []
        last_common_comp = 99
        # first establish common prefix
        for ft in self.filetypes:
            comps = self.dest[ft].split('/')[1:]
            if not firstcomps:
                firstcomps = comps
            for i in range(1,min(last_common_comp, len(comps)):
                if comps[i] != firstcomps[i]:
                    last_common_comp = i
                    break
        last_common_comp += 1

        for ft in self.filetypes:
            comps = self.dest[ft].split('/')[1:]
            for i in range(len(comps)-1,-1,-1):
                if not comps[i].startswith('$'):
                    self.constparts[ft] = '/'.join(comps[last_common_comps:i+1]
                    self.mdparts[ft] = '/'.join(comps[i+1:])
            
         self.common_prefix = '/' + '/'.join(firstcomps[:maxcomps])

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
            
     def write_declad_cfg():
         

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
