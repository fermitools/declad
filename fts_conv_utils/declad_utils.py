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

