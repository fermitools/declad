import importlib
import os
import re
import sys

# setup so we can import plugins and our mock files
sys.path.append(os.path.dirname(__file__)+"/plugins")
sys.path.append(os.path.dirname(__file__)+"/mocks")

def wildcard_list_to_re( wclist: str, subdirpat:str=""  ) -> str: 
    """ 
        Take a list of wildcard/glob patterns, and optional subdirectory
        regex and return a compiled regular expression that matches any 
        of those wildcards in directories matching that subdirectory re.
    """
    
    reparts = []
    for wc in wclist:
        repart = wc.replace(".","\\.").replace("*", ".*").replace("?",".")
        if subdirpat:
           repart = f"{subdirpat}/{repart}"
        reparts.append( repart )
    return re.compile(f"({'|'.join(reparts)})")

# This has to work for at least:
# ----------------------
# ${CAF.base_release}
# ${DAQ2RawDigit.base_release}
# ${file_id[10 div 2]}
# ${NOVA.decaf_skim}
# ${Nova.DetectorID}
# ${NOvA.detectorID}
# ${NOVA.DetectorID}
# ${NOVA.Release}
# ${NOVA.Special}
# ${Online.Detector}
# ${Online.Stream[2]}
# ${run_number}
# ${run_number div 100[6]}
# ${Simulated.base_release}
# ${Simulated.generator}
# ${Simulated.genietune}
# Block${laser_scan.block_number[2]}
# Layer${laser_scan.layer_number[2]}
#
def convert_fts(comp, metadata):
    """ convert things like ${foo/12[6]} to 6th char of (UPS) metadata foo divided by12 """
    divby = None
    pickchar1 = None
    pickchar2 = None
 
    pos = comp.find('[')
    if pos > 0:
        pick = comp[pos+1:-1]
        pos2 = pick.find(' div ')
        if pos2 > 0:
            pickchar1 = int(comp[pos+1:pos2])
            pickchar2 = pickchar1 + int(comp[pos2+5:-1])
        else
            pickchar1 = int(comp[pos+1:-1])
            pickchar2 = pickchar1+1
        comp = comp[0:pos]

    pos = comp.find(" div ")
    if pos > 0:
        divby = comp[pos+5:]
        comp = comp[0:pos]
        

    comp = comp.replace('${','%(').replace('}',')s')
    val = comp % metadata
    # this is assuming the fields are in the formatting metadata... we might need the
    # SAM metadata? thats annoying...

    if divby:
        val = str(int(float(val) / float(divby)))

    if pickchar1:
        val = val[pickhar1:pickchar2]

    return val

class fake_filestate:
    """ Used to pass filename into Fermi-FTS metadata extractor plugins"""
    def __init__(self, filename):
        self._filename = filename
    def getFilename(self):
        return self._filename

def use_extractor(name, file):
    mod = importlib.import_module(name)   
    pass

def base_metadata(filename, namespace, samish = False):
    """ get file size and checksum metadata for a file from local filesystem """
    size = os.stat(filename).st_size
    with popen("xrdadler32 filename", "r") as fd:
        line = fd.readline().strip()
        checksum = line[0:line.find(" ")]
    if samish:
        return { "file_name": filename, "file_size": size, "checksum": ["adler32:" + checksum ]}
    else:
        return { "name": filename, "namespace": namespace, "size": size, "checksums": { "adler32": checksum }}
    

if __name__ == '__main__':
    myre = wildcard_list_to_re( ["a*.root", "b*.root"], "s.*b" )
    # check files which should match
    for a in ["sub/apple.root", "sub/bottle.root"]:
        if myre.match(a):
            print(f"{a} ok")
        else:
            print(f"{a} fail")
    # check files which should NOT match
    for a in ["sub/cad.root", "sub/junk.root","wrong/apple.root"]:
        if myre.match(a):
            print(f"{a} fail")
        else:
            print(f"{a} ok")

