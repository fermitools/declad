try:
    import custom
    assert(custom.__file__)
except:
    raise AttributeError("Unable to import 'custom', did you forget to symlink experiment.py as __init__.py?")

import re
from pythreader import PyThread, synchronized, Primitive, Task, TaskQueue
from tools import runCommand
import json, hashlib, traceback, time, os, pprint, textwrap
import rucio_client, metacat_client, samweb_client
from samweb_client import SAMDeclarationError
from logs import Logged
from xrootd_scanner import XRootDScanner
from lfn2pfn import lfn2pfn
from datetime import datetime, timezone
from rucio.common.exception import DataIdentifierAlreadyExists, DuplicateRule, FileAlreadyExists


from pythreader import version_info as pythreader_version_info
#if pythreader_version_info < (2,15,0):
#    raise ModuleNotFoundError("pythreader version 2.15.0 or newer is required")

class MoverTask(Task, Logged):
    
    RequiredMetadata = [["checksum","checksums"], ["file_size","size"], ["runs","core.runs", "rs.runs"]]
    DefaultMetaSuffix = ".json"
    # remember last dataset we created in to reduce repeats
    last_created_rucio_dataset = None 
    last_created_metacat_dataset = None 
    
    def __init__(self, config, filedesc):
        Task.__init__(self, filedesc)
        Logged.__init__(self, name=f"MoverTask[{filedesc.Name}]")

        self.FileDesc = filedesc
        self.Config = config
        self.MetaSuffix = config.get("meta_suffix", ".json")
        self.RucioConfig = config.get("rucio", {})
        self.Activity = self.RucioConfig.get("activity", "")
        self.SAMConfig = config.get("samweb", {})
        self.QuarantineLocation = config.get("quarantine_location")
        self.SourceServer = config["source_server"]
        self.DestServer = config.get("destination_server") or self.SourceServer
        self.TransferProto = config.get("transfer_proto","root")
        
        # source and destination paths in xrootd namespace
        self.SrcRootPath = config["source_root_path"]
        self.DstRootPath = config["destination_root_path"]
        
        self.TransferTimeout = config.get("transfer_timeout", 120)
        self.LowecaseMetadataNames = config.get("lowercase_meta_names", False)
        self.Error = None
        self.Failed = False
        self.Status = "created"
        self.EventLog = []              # [(event, t, info), ...]
        self.EventDict = {}
        self.RetryAfter = None          # do not resubmit until this time
        self.KeepUntil = None           # keep in memory until this time
        self.DefaultCategory = config.get("default_category")       # default metadata category for unexpeted uncategorized metadata attrs
        self.timestamp("created")


    def last_event(self, name=None):
        if self.EventLog:
            if name is None:
                return self.EventLog[-1]
            else:
                last_record = (None, None, None)
                for event, t, info in self.EventLog:
                    if event == name:
                        last_record = (event, t, info)
                return last_record
        else:
            return None, None, None

    @property
    def name(self):
        return self.FileDesc.Name
        

    def undid(self, did):
        return did.split(":", 1)

    def destination_rel_path(self, scope, desc, metadata):
        """
        From Rucio lib/rucio/rse/protocols/protocol.py
        
        Given a LFN, turn it into a sub-directory structure using a hash function.

        This takes the MD5 of the LFN and uses the first four characters as a subdirectory
        name.
        
        :function str: function to apply. If None - standard Rucio hash function for deterministic RSEs
        :param scope: Scope of the LFN.
        :param desc: File descriptor from the xrootd scanner, includes file name
        :returns: Path for use in the PFN generation.
        """
        name = desc.Name
        hstr = hashlib.md5(('%s:%s' % (scope, name)).encode('utf-8')).hexdigest()
        if scope.startswith('user') or scope.startswith('group'):
            scope = scope.replace('.', '/')
        return '%s/%s/%s/%s' % (scope, hstr[0:2], hstr[2:4], name)
        
    def get_file_size(self, server, path):
        if self.TransferProto == 'root':
            scanner = XRootDScanner(server, self.Config["scanner"])
            return scanner.getFileSize(path)
        elif self.TransferProto == 'https':
            stat_command = f"gfal-stat https://{server}/{path}"
            self.log(f"Running {stat_command}")
            status, out = runCommand(stat_command, self.TransferTimeout, self.debug)
            lines = [x.strip() for x in out.split("\n")]
            for line in lines:
                self.log(f"stat line: {line}")
                if line.find("Size:") >= 0:
                    fields = re.split(r"\s+", line)
                    self.log(f"found size {fields[1]}")
                    return int(fields[1])
        return None

    def run(self):
        # import a template_tags() routine if present, otherwise nothing local..
        try:
            from custom import template_tags
        except:
            self.log("Notice: no template_tags callout in custom.py; adding default empty one...")
            def template_tags(metadata):
                return {}

        #self.debug("started")
        self.timestamp("started")
        self.Failed = False
        self.Error = None
        self.TaskStarted = time.time()
        #self.debug("time:", time.time())
        
        filename, relpath = self.FileDesc.Name, self.FileDesc.RelPath
        self.debug("FileDescritor:", self.FileDesc)

        #
        # Get metadata and parse
        #
        
        meta_suffix = self.Config.get("meta_suffix", self.DefaultMetaSuffix)
        meta_tmp = self.Config.get("temp_dir", "/tmp") + "/" + self.FileDesc.Name + meta_suffix
        meta_path = self.FileDesc.path(self.SrcRootPath) + meta_suffix
        download_cmd = self.Config["download_command_template"] \
            .replace("$server", self.SourceServer) \
            .replace("$src_path", meta_path) \
            .replace("$dst_path", meta_tmp)
        self.debug("download command:", download_cmd)

        self.timestamp("downloading metadata")

        ret, output = runCommand(download_cmd, self.TransferTimeout, self.debug)
        self.debug("metadata download command:", download_cmd)
        if ret:
            return self.failed("Metadata download failed: %s" % (output,))
        
        try:
            metadata = json.load(open(meta_tmp, "r"))
        except Exception as e:
            return self.failed(f"Metadata loading error: {e}")
        finally:
            os.remove(meta_tmp)

        # strip whitespace from around the attribute names
        metadata = {key.strip():value for key, value in metadata.items()}

        for rlst in self.Config.get("required_metadata", self.RequiredMetadata):
            found=False
            for rm in rlst:
                if rm in metadata:
                    found= True
                if rm in metadata.get("metadata",{}):
                    found= True
            if not found:
                return self.quarantine(f"any of {rlst} missing from metadata")

        #
        # Check file size
        #
        file_size = metadata.get("file_size", metadata.get("size"))

        if not isinstance(file_size, int) or file_size <= 0:
            return self.quarantine(f"Invalid file size in metadata: {file_size}")
        
        if file_size != self.FileDesc.Size:
            return self.failed(f"Scanned file size {self.FileDesc.Size} differs from metadata: {file_size}")

        #
        # Convert to MetaCat format
        #
        try:
            metacat_meta = custom.metacat_metadata(self.FileDesc, metadata, self.Config)   # massage meta if needed
        except Exception as e:
            return self.quarantine(f"Error converting metadata to MetaCat: {e}")

        try:    file_scope = custom.get_file_scope(self.FileDesc, metadata, self.Config)
        except Exception as e:
            return self.quarantine("can not get file scope. Error: %s. Metadata runs: %s" % (e.what(), metadata.get("runs"),))
            
        did = file_scope + ":" + filename
            
        if "checksum" in metadata:
            adler32_checksum = metadata["checksum"]
        if "checksums" in metadata:
            adler32_checksum = metadata["checksums"]["adler32"]
        if isinstance(adler32_checksum, list) and adler32_checksum:
             adler32_checksum = adler32_checksum[0]

        if ':' in adler32_checksum:
            type, value = adler32_checksum.split(':', 1)
            assert type == "adler32"
            adler32_checksum = value


        # EOS expects URL to have double slashes: root://host:port//path/to/file
        src_data_path = self.FileDesc.path(self.SrcRootPath)
        rel_path_function = self.Config.get("rel_path_function")
        dest_root_path = self.DstRootPath
        self.debug("")
        if rel_path_function == "hash":
            dest_rel_path = self.destination_rel_path(file_scope, self.FileDesc, metacat_meta)
        elif rel_path_function == "template":
            mhstr = hashlib.md5(('%s:%s' % (file_scope, filename)).encode('utf-8')).hexdigest()
            shstr = hashlib.sha256(('%s:%s' % (file_scope, filename)).encode('utf-8')).hexdigest()
            meta_dict = metacat_meta.copy()
            meta_dict.update(dict(
                scope = file_scope,
                name = filename,
                md5hash = "%s/%s" % (mhstr[0:2], mhstr[2:4]),
                sha256hash = "%s/%s" % (shstr[0:2], shstr[2:4]),
            ))
            # add plugin defined tags...
            meta_dict.update(template_tags(metadata))
            # push metadata layer up...
            if "metadata" in meta_dict:
                meta_dict.update(meta_dict["metadata"])
            
            self.log(f'converting {self.Config["rel_path_pattern"]} with {repr(meta_dict)}')
            dest_rel_path = self.Config["rel_path_pattern"] % meta_dict
        else:
            raise ValueError(f"Unknown relative path function {rel_path_function}. Accepted: hash or template")
        dest_data_path = dest_root_path + "/" + dest_rel_path
        dest_dir_abs_path = dest_data_path.rsplit("/", 1)[0]  
        data_dst_url = self.TransferProto + "://" + self.DestServer + "/" + dest_data_path     
        if self.SourceServer is None or self.SourceServer == "localhost":
            data_src_url = "file:///" + src_data_path
        else:
            data_src_url = self.TransferProto + "://" + self.SourceServer + "/" + src_data_path
        
        #
        # check if the dest data file exists and has correct size
        #
        
        try:    
            dest_size = self.get_file_size(self.DestServer, dest_data_path)
            self.debug("Destination data file size:", dest_size)
        except Exception as e:
            return self.failed(f"Can not get file size at the destination: {e}")
            
        #if dest_size is not None:
        #    self.debug(f"data file exists at the destination {dest_data_path}, size: {dest_size}")

        do_move_files = self.Config.get("move_files", True)
        if dest_size != file_size:
            if dest_size is not None:
                self.log(f"destination file exists but has incorrect size {dest_size} vs. {file_size}")

            #
            # copy data
            #
            self.timestamp("creating dirs")
            create_dirs_command = self.Config["create_dirs_command_template"]   \
                .replace("$server", self.DestServer)    \
                .replace("$path", dest_dir_abs_path)
            #self.debug("create dirs command:", create_dirs_command)

            ret, output = runCommand(create_dirs_command, self.TransferTimeout, self.debug)
            #if ret:
            #    self.debug("create dirs failed (will be ignored assuming it already exists): %s" % (output,))

            copy_cmd = self.Config["copy_command_template"] \
                .replace("$dst_url", data_dst_url)  \
                .replace("$src_url", data_src_url)  \
                .replace("$dst_data_path", dest_data_path)   \
                .replace("$src_data_path", src_data_path)   \
                .replace("$dst_rel_path", dest_rel_path) \
                .replace("$adler32_checksum", adler32_checksum) \
                .replace("$file_size", str(file_size) )
            #self.debug("copy command:", copy_cmd)

            self.timestamp("transferring data")

            #self.debug("copy command:", copy_cmd)
            ret, output = runCommand(copy_cmd, self.TransferTimeout, self.debug)
            if ret:
                return self.failed("Data copy failed: %s" % (output,))

            self.donewith(src_data_path)

            self.log("data transfer complete")
            try:    
                dest_size = self.get_file_size(self.DestServer, dest_data_path)
                self.debug("Destination data file size:", dest_size)
            except Exception as e:
                return self.failed(f"Can not get file size at the destination: {e}")

            if dest_size != file_size:
                 return self.failed("Transferred file has wrong size")            
        else:
            self.log("data file already exists at the destination and has correct size. Not overwriting")

        #
        # Do the declarations
        #
        #
        # declare to SAM
        #
        file_id = None
        
        do_declare_to_sam = self.Config.get("declare_to_sam", True)
        if do_declare_to_sam:
            sclient = samweb_client.client(self.SAMConfig)
        else:
            sclient = None

        if sclient is not None:
            self.timestamp("declaring to SAM")
            existing_sam_meta = sclient.get_file(filename)

            if existing_sam_meta is not None and not "error" in existing_sam_meta:
                try:    file_id = str(existing_sam_meta["file_id"])
                except KeyError:
                    return self.quarantine("Existing SAM metadata does not contain file_id")
                sam_size = existing_sam_meta.get("file_size")

                sam_adler32 = dict(ck.split(':', 1) for ck in existing_sam_meta.get("checksum", [])).get("adler32").lower()
                if isinstance(adler32_checksum, list) and adler32_checksum:
                     adler32_checksum = adler32_checksum[0]
                adler32_checksum = adler32_checksum.replace("adler32:","")
                if sam_size != file_size or adler32_checksum != sam_adler32:
                    return self.quarantine("already declared to SAM with different size and/or checksum file_size %s vs sam %s cheksum %s vs sam %s  " % (file_size, sam_size, adler32_checksum, sam_adler32))
                else:
                    self.log("already delcared to SAM with the same size/checksum")
            else:
                s_metadata = custom.sam_metadata(self.FileDesc, metadata, self.Config)
                if do_declare_to_sam:
                    self.log(f"trying to declare to SAM: {repr(s_metadata)}")
                    try:    file_id = sclient.declare(s_metadata)
                    except SAMDeclarationError as e:
                        return self.failed(str(e))
                    self.log("declared to SAM. File id:", file_id)
                else:
                    self.debug("would declare to SAM:", json.dumps(s_metadata, indent=4, sort_keys=True))

            #
            # Add SAM location
            #
            sam_location_template = self.Config.get("sam_location_template")
            do_add_locations = do_declare_to_sam and self.Config.get("add_sam_locations", True)
            dst_data_dir = dest_data_path.rsplit('/', 1)[0]
            dst_rel_dir = dest_rel_path.rsplit('/', 1)[0]
            if sam_location_template and do_add_locations:
                sam_location = sam_location_template \
                    .replace("$dst_rel_path", dest_rel_path) \
                    .replace("$dst_data_path", dest_data_path) \
                    .replace("$dst_data_dir", dst_data_dir) \
                    .replace("$dst_rel_dir", dst_rel_dir)
                self.debug(f"Adding location for {filename}: {sam_location}")
                try:    
                    try:
                        sclient.add_location(sam_location, name=filename)
                    except:
                        self.debug("error in add_location:")
                        self.debug(traceback.format_exc())
                        raise
                except SAMDeclarationError as e:
                    return self.failed(str(e))
                self.log("added SAM location:", sam_location)
                
                # debug
                #self.debug("checking file locations...")
                try:
                    locations = sclient.locate_file(filename)
                    if sam_location not in locations:
                        self.log("Location", sam_location, "not found in SAM locations:")
                        for loc in locations:
                            self.debug("   ", loc)
                        return self.failed("SAM location verification failed")
                    else:
                        #self.debug("location found")
                        pass
                except:
                    self.debug("locate_file failed:\n", traceback.format_exc())

        #
        # get handles for rucio/metacat if we're doing them
        #
        do_declare_to_metacat = self.Config.get("declare_to_metacat", True)
        if do_declare_to_metacat:
            mclient = metacat_client.client(self.Config)
        else:
            mclient = None

        do_declare_to_rucio = self.RucioConfig.get("declare_to_rucio", True)
        if do_declare_to_rucio:
            rclient = rucio_client.client(self.RucioConfig)
        else:
            rclient = None
        #
        # create dataset if does not exist
        #
        metacat_dataset_did = custom.metacat_dataset( self.FileDesc, metadata, self.Config)
        dataset_scope, dataset_name = metacat_dataset_did.split(":")

        self.log(f"metacat dataset: {dataset_scope}:{dataset_name} vs {self.last_created_metacat_dataset}")
        if f"{dataset_scope}:{dataset_name}" != self.last_created_metacat_dataset:
            self.last_created_metacat_dataset = f"{dataset_scope}:{dataset_name}" 
            if mclient is not None:
                # create in metacat first...
                try:
                    mclient.create_dataset(f"{dataset_scope}:{dataset_name}")
                except metacat_client.AlreadyExistsError:
                    pass

        rucio_dataset_did = custom.rucio_dataset(self.FileDesc, metadata, self.Config)
        dataset_scope, dataset_name = rucio_dataset_did.split(":")

        self.log(f"rucio dataset: {dataset_scope}:{dataset_name} vs {self.last_created_rucio_dataset}")
        if f"{dataset_scope}:{dataset_name}" != self.last_created_rucio_dataset:
            if rclient is not None:
                try:    
                    added = False
                    rclient.add_did(dataset_scope, dataset_name, "DATASET")
                    added = True
                except DataIdentifierAlreadyExists:
                    pass
                except Exception as e:
                    return self.quarantine(f"Error in creating Rucio dataset {dataset_scope}:{dataset_name}: {e}")
            
                else:
                    self.log(f"Rucio dataset {dataset_scope}:{dataset_name} created")
                for target_rse in self.RucioConfig["target_rses"]:
                    try:
                        rdict = {"scope":dataset_scope, "name":dataset_name}
                        if self.Activity:
                            self.log(f"adding rule with activity {self.Activity}")
                            rclient.add_replication_rule([rdict], 1, target_rse, activity=self.Activity)
                        else:
                            self.log(f"adding rule with out activity")
                            rclient.add_replication_rule([rdict], 1, target_rse)
                    except DuplicateRule:
                        pass
                    except Exception as e:
                        return self.quarantine(f"Error in creating Rucio replication rule -> {target_rse}: {e}")
                    else:
                        self.log(f"replication rule -> {target_rse} created")
        #
        # declare to MetaCat
        #
        if mclient is not None:
            if do_declare_to_metacat:
                self.timestamp("declaring to MetaCat")
                existing_metacat = mclient.get_file(did=did)
                if existing_metacat:
                    if existing_metacat["size"] != file_size or existing_metacat.get("checksums", {}).get("adler32") != adler32_checksum:
                        self.quarantine("already declared to MetaCat with different size and/or checksum")
                    else:
                        self.log("already declared to MetaCat")
                else:
                    metacat_meta = custom.metacat_metadata(self.FileDesc, metadata, self.Config)   # massage meta if needed
                    file_info = {
                            "namespace":    file_scope,
                            "name":         filename,
                            "metadata":     metacat_meta,
                            "size":         file_size,
                            "checksums":    {   "adler32":  adler32_checksum   },
                        }
                    if file_id is not None:
                        file_info["fid"] = str(file_id)
                    self.debug("about to mclient.declare_files dataset_did %s with file_info: %s" % (metacat_dataset_did, repr(file_info)))
                    try:    
                        file_info = mclient.declare_file(
                            fid=file_id, namespace=file_scope, name=filename, 
                            metadata=metacat_meta,
                            dataset_did=metacat_dataset_did,           
                            parents=metadata.get("parents", []),
                            size=file_size, checksums={ "adler32":  adler32_checksum }
                        )
                    except Exception as e:
                        return self.failed(f"MetaCat declaration failed: {e}")
                    self.log("file declared to MetaCat")

            else:
                self.debug("would declare to MetaCat")
                self.debug("Name, namespace, fid:", filename, file_scope, file_id)
                self.debug(json.dumps(metacat_meta, indent=2, sort_keys=True))

        #
        # declare to Rucio
        #
        if rclient is not None:

            if do_declare_to_rucio:
                #print(rclient.whoami())

                self.timestamp("declaring to Rucio")

                # declare file replica to Rucio
                drop_rse = self.RucioConfig["drop_rse"]
                self.log(f"calling add_replica( {drop_rse}, {file_scope}, {filename}, {file_size}, {adler32_checksum})")
                rclient.add_replica(drop_rse, file_scope, filename, file_size, adler32_checksum)
                self.log(f"File replica declared in drop rse {drop_rse}")

                # add the file to the dataset
                try:
                    rclient.attach_dids(dataset_scope, dataset_name, [{"scope":file_scope, "name":filename}])
                except FileAlreadyExists:
                    self.log("File was already attached to the Rucio dataset")
                else:
                    self.log("File attached to the Rucio dataset")
            else:
                self.debug("would declare to Rucio")

        self.timestamp("removing sources")

        do_remove_sources = self.Config.get("remove_sources", True)

        rmcommand = self.Config["delete_command_template"]	\
            .replace("$server", self.SourceServer)	\
            .replace("$path", meta_path)
        if do_remove_sources:
            ret, output = runCommand(rmcommand, self.TransferTimeout, self.debug)
            if ret:
                return self.failed("Remove source metadata failed: %s" % (output,))
        else:
            self.debug("would remove source metadata:", rmcommand)

        rmcommand = self.Config["delete_command_template"]	\
            .replace("$server", self.SourceServer)	\
            .replace("$path", src_data_path)
        if do_remove_sources:
            ret, output = runCommand(rmcommand, self.TransferTimeout, self.debug)
            if ret:
                return self.failed("Remove source ata failed: %s" % (output,))

        else:
            self.debug("would remove source data file:", rmcommand)

        self.Manager = None
        self.timestamp("complete")

    def donewith(self, src_data_path):
        """ tell system buffer cache we"re done with file """

        if self.Config["scanner"].get("type") == "local":
            self.log(f"calling fadvise w/ dontneed for {src_data_path}")
            with open(src_data_path) as pf:
                os.posix_fadvise(pf.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    @synchronized
    def timestamp(self, event, info=None):
        self.EventDict[event] = self.LastUpdate = t =  time.time()
        self.EventLog.append((event, t, info))
        self.log("-----", event)
        #self.debug(event, "info:", info)
        self.Status = event

    @synchronized
    def failed(self, error):
        self.Failed = True
        self.Error = error
        self.log("failed with error:", error or "")
        self.timestamp("failed", error)

    @synchronized
    def quarantine(self, reason = None):
        # quarantine data only. we can leave the metadata in place
        self.Error = reason or self.Error
        self.Failed = True

        src_path = self.FileDesc.path(self.SrcRootPath)
        # tell buffer cache to drop this file
        self.donewith(src_data_path)
        if self.QuarantineLocation:

            # quarantine the metadata file
            meta_path = src_path + self.MetaSuffix
            qmeta_path = self.QuarantineLocation + "/" + self.FileDesc.Name + self.MetaSuffix
            if self.FileDesc.Server is None:
                cmd = "mv %s %s" % (
                    meta_path, qmeta_path
                )
            else:
                cmd = "xrdfs %s mv %s %s" % (
                    self.FileDesc.Server,
                    meta_path, qmeta_path
                )
            ret, output = runCommand(cmd, self.TransferTimeout, self.debug)
            if ret:
                return self.failed("Quarantine for metadata file %s failed: %s" % (self.FileDesc.Name + self.MetaSuffix, output))

            # quarantine the data file
            path = src_path
            qpath = self.QuarantineLocation + "/" + self.FileDesc.Name
            if self.FileDesc.Server is None:
                cmd = "mv %s %s" % (
                    path, qpath
                )
            else:
                cmd = "xrdfs %s mv %s %s" % (
                    self.FileDesc.Server,
                    path, qpath
                )
            ret, output = runCommand(cmd, self.TransferTimeout, self.debug)
            if ret:
                return self.failed("Quarantine for data file %s failed: %s" % (self.FileDesc.Name, output))

            self.timestamp("quarantined", self.Error)
            
        else:
            raise ValueError("Quarantine directory unspecified")

class Manager(PyThread, Logged):
    
    DEFAULT_LOW_WATER_MARK = 5
    
    def __init__(self, config, history_db):
        PyThread.__init__(self, name="Mover")
        Logged.__init__(self, name="Mover")
        self.Config = config
        capacity = None             # config.get("queue_capacity") possible deadlock otherwise
        max_movers = config.get("max_movers", 10)
        stagger = config.get("stagger", 0.2)
        self.TaskQueue = TaskQueue(max_movers, capacity=capacity, stagger=stagger, delegate=self)
        self.RetryCooldown = int(config.get("retry_cooldown", 300))
        self.TaskKeepInterval = int(config.get("keep_interval", 24*3600))
        self.LowWaterMark = config.get("low_water_mark", self.DEFAULT_LOW_WATER_MARK)
        self.HistoryDB = history_db
        self.NextRetry = {}	                # name -> t
        self.RecentTasks = {}               # name -> task
        self.Stop = False

    def task(self, name):
        return self.RecentTasks.get(name)

    def stop(self):
        self.Stop = True
        self.wakeup()
        
    def quarantined(self):
        qlocation = self.Config.get("quarantine_location")
        if not qlocation:
            return [], "Quarantine not configured"
        scanner = XRootDScanner(self.Config["source_server"], self.Config["scanner"])
        error = None
        files = []
        try:    files = scanner.scan(qlocation)		# returns file descriptors
        except Exception as e:
            error = str(e)
        return files or [], error
            
    @synchronized
    def recent_tasks(self):
        return sorted(self.RecentTasks.values(), key=lambda t: -t.last_event()[1] or 0)
        
    @synchronized
    def current_transfers(self):
        waiting, active = self.TaskQueue.tasks()
        return active + waiting

    def low_water(self):
        return len(self.TaskQueue) < self.LowWaterMark

    @synchronized
    def add_files(self, files_dict):
        #
        # WARNING: this can cause a deadlock of the queue capacity is limited
        #
        
        # files_dict: {name:desc}
        # purge expired retry-after entries and the list of found but delayed files
        #self.RetryAfter = dict((name, t) for name, t in self.RetryAfter.items() if t > time.time())
        #self.Delayed = dict((name, t) for name, t in self.Delayed.items() if t > time.time())
        waiting, active = self.TaskQueue.tasks()
        in_progress = set(t.FileDesc.Name for t in waiting + active)
        now = time.time()
        self.NextRetry = {name:t for name, t in self.NextRetry.items() if t > now}
        nqueued = 0
        for name, filedesc in files_dict.items():
            name = filedesc.Name
            if name not in in_progress and name not in self.NextRetry:
                task = MoverTask(self.Config, filedesc)     # retry the file: create new task with new FileDesc to reflect fresh scan results
                task.KeepUntil = now + self.TaskKeepInterval
                self.RecentTasks[name] = task
                self.NextRetry[name] = now + self.RetryCooldown
                self.TaskQueue.addTask(task)
                task.timestamp("queued")
                nqueued += 1
        self.log("%d new files queued out of %d found by the scanner" % (nqueued, len(files_dict)))

    @synchronized
    def taskEnded(self, queue, task, _):
        if task.Failed:
            return self.taskFailed(queue, task, None, None, None)
        else:
            self.log("\nMover done:", task.name, "\n\n")
            task.KeepUntil = time.time() + self.TaskKeepInterval
            task.RetryAfter = time.time() + self.RetryCooldown
            desc = task.FileDesc
            self.HistoryDB.file_done(desc.Name, desc.Size, task.Started, task.Ended)

    @synchronized
    def taskFailed(self, queue, task, exc_type, exc_value, tb):
        if exc_type is not None:
            error = "".join(traceback.format_exception(exc_type, exc_value, tb))
            error = "\n" + textwrap.indent(error, "    ")
        else:
            # the error already logged by the task itself
            error = task.Error
        task.KeepUntil = time.time() + self.TaskKeepInterval
        task.RetryAfter = time.time() + self.RetryCooldown
        desc = task.FileDesc
        #self.debug("task failed:", task, "   will retry after", time.ctime(self.RetryAfter[task.name]))
        self.log(f"\nMover failed: {task.name} status: {task.Status} error:", error, "\n\n")
        #self.debug("taskFailed: error:", error)
        if task.Status == "quarantined":
            self.HistoryDB.file_quarantined(desc.Name, task.Started, error, task.Ended)
        else:
            self.HistoryDB.file_failed(desc.Name, desc.Size, task.Started, error, task.Ended)

    @synchronized
    def purge_memory(self):
        nbefore = len(self.RecentTasks)
        self.RecentTasks = {name: task for name, task in self.RecentTasks.items() if task.KeepUntil >= time.time()}
        nafter  = len(self.RecentTasks)
        self.log("purge_memory: known files before and after:", nbefore, nafter)

    def run(self):
        while not self.Stop:
            self.sleep(60)
            self.purge_memory()
        self.log("stopping ...")
        self.TaskQueue.drain()
        self.log("ending thread")
