import os, sys, re, time

class patchit:
    """ context manager for applying / removing a patch"""
    def __init__(self, base, patchfile):
        self.patchfile = patchfile
        self.base = base
    def __enter__(self):
        if self.patchfile:
            os.system("cd {self.base} && patch -p1 < {patchfile}");
    def __exit__(self,*args):
        if self.patchfile:
            os.system("cd {self.base} && patch -R -p1 < {patchfile}");

# regexps for watch_log...
re_nfiles  = re.compile(r"scanner returned [1-9] file descriptors")
re_extract = re.compile(r"Running:.*demo_meta_extractor.sh")
re_cpcmd   = re.compile(r"runCommand: xrdcp.*[0-9].txt")
re_after   = re.compile(r"known files before and after: [1-9]")
re_trace   = re.compile(r"Traceback")

def watch_log(lf, ext_flag):
    state = 0

    if not os.path.exists(lf):
        return False

    let_logfile_grow(lf)

    with open(lf, "r") as lfd:
        for line in lfd.readlines():
            print(f"saw: {line}")
            if re_trace.search(line):
                raise AssertionError("Saw Traceback in log")

            if re_nfiles.search(line) and state == 0:
                print(f"watch_log => 1: {line}")
                state = 1

            if  ext_flag and re_extract.search(line) and state == 1:
                print(f"watch_log => 2: {line}")
                state = 2

            if re_cpcmd.search(line) and state == (2 if extflag else 1):
                print(f"watch_log => 3: {line}")
                state = 3

            if re_after.search(line) and state == 3:
                print(f"watch_log => done: {line}")
                # saw everything we expected
                return True

    print(f"Error: only got to state: {state}")
    return False

def cleanup_dirs(dlist):
    for d in dlist:
        try:
            os.rmdir(d)
        except:
            return False

def run(cmd):
    print(f"Running: {cmd}")
    os.system(cmd)

def let_logfile_grow( lf ):
    """ if logfile is growing, wait up to 3 minutes..."""
    oldsize = 0
    time.sleep(2)
    size  = os.stat(lf)[6]
    if size > oldsize:
        time.sleep(330)   # just sleep a little over 5 minutes for now.
    size  = os.stat(lf)[6]
    print(f"log size {size}, returning...")
    return


def generic_case( base, custom, patchfile, generator, nfiles, ext_flag, fail):

    res = False
    # setup custom module link
    try:
        os.unlink( f"{base}/custom/__init__.py" )
    except FileNotFoundError:
        pass

    if custom:
         os.symlink(f"{base}/custom/{custom}.py" , f"{base}/custom/__init__.py")

    with patchit(base, patchfile):
        run( generator )
        try:
            os.unlink(f"{base}/logs/declad.log")
        except FileNotFoundError:
            pass
        run(f"cd {base} && ./restart.sh")

        try:
           res = watch_log(f"{base}/logs/declad.log", ext_flag)
        except:
           res = False

        run(f"cd {base} && ./stop.sh")

    # cleanup to not confuse later tests, and to make sure
    # dropbox/quarantine are empty
    if not cleanup_dirs([f"{base}/dropbox", f"{base}/quarantine"]):
        os.system(f"rm -rf {base}/dropbox {base}/quarantine")
        res = False
    os.mkdir(f"{base}/dropbox")
    os.mkdir(f"{base}/quarantine")

    assert( res != fail )

base = "/home/hypotpro/declad_848"


def test_no_custom_init_py_fails():
    generic_case(base, None, None, "make_test_ext_data.sh", 5, True, True)
    with open(f"{base}/logs/nohup.out") as f:
        data = f.read()
    assert(data.find("did you forget to symlink") > 0)

def test_hypot_extractor():
    generic_case(base, "hypot", None, "make_test_ext_data.sh", 5, True, False)

