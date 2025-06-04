import os, sys, re, time, glob

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# support code...

class patchit:
    """ context manager for applying / removing a patch"""
    def __init__(self, base, patchfile):
        if patchfile:
            patchfile = f"{prefix}/tests/patches/{patchfile}"
        print(f"(patchit( {base}, {patchfile})...")
        self.patchfile = patchfile
        self.base = base
    def __enter__(self):
        if self.patchfile:
            cmd = f"cd {self.base} && patch -p1 < {self.patchfile}"
            print(f"patchit: cmd: {cmd}")
            os.system(cmd);
    def __exit__(self,*args):
        if self.patchfile:
            cmd = f"cd {self.base} && patch -R -p1 < {self.patchfile}"
            print(f"patchit: cmd: {cmd}")
            os.system(cmd);

# regexps for watch_log...
re_nfiles  = re.compile(r"scanner returned [1-9][0-9]* file descriptors")
re_extract = re.compile(r"Running:.*demo_meta_extractor.sh")
re_cmd     = re.compile(r"runCommand: ")
re_trace   = re.compile(r"Traceback")
re_xfer_s  = re.compile(r"transferring data")
re_xfer_e  = re.compile(r"data transfer complete")
re_after   = re.compile(r"known files before and after: [1-9]")
re_filesize= re.compile(r"File size is lower than configured")

def readline_wait(fd):
    # do tail -f style read...
    res = fd.readline()
    count = 0
    while not res:
        count = count + 1
        if count > 20:
            return ""
        time.sleep(10)
        res = fd.readline()
    return res

def watch_log(lf, ext_flag, nfiles):

    if not os.path.exists(lf):
        return False

    state = 0
    completed_count = 0

    with open(lf, "r") as lfd:
        while ( line :=  readline_wait( lfd ) ):
            #print(f"saw: {line}")
            if re_trace.search(line):
                print("Saw Traceback in log")
                return False

            if re_filesize.search(line):
                print("Saw minimum file size error in log")
                return False

            if re_nfiles.search(line) and state == 0:
                print(f"watch_log => 1: {line}")
                state = 1

            if ext_flag and re_extract.search(line) and state == 1:
                print(f"watch_log => 2: {line}")
                state = 2

            if re_cmd.search(line):
                print(f"watch_log: {line}")

            if state in (1,2) and re_xfer_s.search(line):
                print(f"watch_log => 3: {line}")
                state = 3

            if state == 3 and re_xfer_e.search(line):
                 print(f"watch_log: {line}")
                 completed_count = completed_count + 1
                 if completed_count == nfiles:
                     print(f"watch_log => 4")
                     state = 4

            if state == 4 and re_after.search(line):
                print(f"watch_log => done: {line}")
                # saw everything we expected
                return True

    print(f"Error: only got to state: {state}")
    return False

def cleanup_dirs(dlist):
    print(f"cleaning dirs: {dlist}")
    for d in dlist:
        try:
            os.rmdir(d)
        except:
            return False
    return True

def run(cmd):
    print(f"Running: {cmd}")
    os.system(cmd)


def generic_case( base, custom, patchfile, generator, nfiles, ext_flag, fail = False):

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
        run(f"cd {base} && ./restart.sh -d")

        res = watch_log(f"{base}/logs/declad.log", ext_flag, nfiles)

        run(f"cd {base} && ./stop.sh")

    # cleanup to not confuse later tests, and to make sure
    # dropbox/quarantine are empty
    hashdirs = glob.glob(f"{base}/dropbox/??")
    if not cleanup_dirs(hashdirs + [f"{base}/dropbox", f"{base}/quarantine"]):
        print("plain rmdir failed on dropbox or quarantine...")
        os.system(f"ls -al {base}/dropbox {base}/quarantine")
        os.system(f"rm -rf {base}/dropbox {base}/quarantine")
        res = False
    os.mkdir(f"{base}/dropbox")
    os.mkdir(f"{base}/quarantine")

    assert( res != fail )


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# actual tests, mostly written with generic_case, above
base = "/home/hypotpro/declad_848"
prefix = os.path.dirname(os.path.dirname(__file__))

def test_no_custom_init_py_fails():
    # this is the test for issue #12
    generic_case(base, None, None, "make_test_ext_data.sh", 5, True, True)
    with open(f"{base}/logs/nohup.out") as f:
        data = f.read()
    assert(data.find("did you forget to symlink") > 0)

def test_hypot_extractor():
    # test for issue #17
    generic_case(base, "hypot", None, "make_test_ext_data.sh", 5, True)


def test_hypot_json_meta():
    # test using new metadata issue #10
    generic_case(base, "hypot", None, "make_test_newdata.sh", 5, False)

def test_dune_json_meta():
    """ test using custom/dune.py for custom """
    generic_case(base, "dune", None, "make_test_newdata.sh", 5, False)

def test_mu2e_json_meta():
    """ test using custom/metacat.py for custom """
    generic_case(base, "mu2e", None, "make_test_newdata.sh", 5, False)

def test_hypot_json_ups():
    generic_case(base, "hypot", None, "make_test_data.sh", 5, False)

def test_hypot_json_hash_meta():
    generic_case(base, "hypot", "config_hashdir.patch", "make_test_hash_newdata.sh", 5, False)

def test_hypot_extractor_subdirs():
    # test for issue #60
    generic_case(base, "hypot", "config_hashdir.patch", "make_test_ext_data.sh --subdirs", 5, True)

def test_hypot_minfilesize():
    # test for issue #63
    generic_case(base, "hypot", "config_minfilesize.patch", "make_test_data.sh", 5, True, True)
    with open(f"{base}/logs/declad.log") as f:
        data = f.read()
    assert(data.find("size is lower than configured minimum") > 0)
