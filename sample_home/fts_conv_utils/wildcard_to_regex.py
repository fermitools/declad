import re

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
