""" routines to convert file metadata between SAM and MetaCat """
import functools
import datetime

def convert_noop(x, md=None):
    """ identity function -- no conversion """
    return x

def convert_date_mc_sam(date, md):
    """ date format convert metacat to sam """
    dt = datetime.datetime.fromtimestamp(date)
    return dt.isoformat()

def convert_date_sam_mc(date):
    """ date format convert sam to metacat """
    dt = datetime.datetime.fromisoformat(date)
    return dt.timestamp()

def convert_checksums_sam_mc(checksums):
    """ special case: checksum conversion"""
    res = {}
    for cs in checksums:
        ctype, value = cs.split(":")
        res[ctype] = value
    return res

def convert_checksums_mc_sam(checksums, md):
    res = []
    for ctype in checksums:
        res.append( "%s:%s" % (ctype, checksums[ctype]))
    return res

g_experiment = None

# constants for run/subrun combination
run_scale_factors = { 
    "mu2e": 1000000, 
    "dune": 100000, 
    "hypot": 1000,
}

def convert_runs_sam_mc(runs):
    """ special case: run/subrun  number conversion"""
    res = []
    m = run_scale_factors[g_experiment]
    for r, sr, typ in runs:
        res.append(m * r + sr)
    return res


def convert_runs_mc_sam( runs, md):
    """ special case: run/subrun  number conversion"""
    typ = md["metadata"].get("core.run_type", md["metadata"].get("md.type", "mc"))
    res = []
    m = run_scale_factors[g_experiment]
    mysubruns = md["metadata"].get("core.runs_subruns",[])
    srcount=0
    for r in runs:
        rn = r
        if srcount < len(mysubruns):
            sr = mysubruns[srcount] % m
        else:
            sr = srcount
        srcount += 1
        res.append( [rn, sr, typ] )
    return res

def convert_parents_sam_mc( parents):
    """ special case: parentage conversion"""
    res = []
    for i in parents:
        res.append( {
            "fid":  str(i["file_id"]),
            "name": i["file_name"],
            "namespace": g_experiment,  # XXX possible bug, what namespace?
        })
    return res


def convert_parents_mc_sam( parents, md):
     """ special case: parentage conversion"""
     res = []
     for i in parents:
         d = { "file_name": i["name"] }
         if str(int(i.get("fid","0"))) == i.get("fid","y"):
             d["file_id"] = int(i["fid"])
         res.append(d)
     return res


class MetadataConverter:
    """ converts metadata between MetaCat and Sam"""
    def __init__(self, experiment):
        global g_experiment
        self.experiment = experiment
        g_experiment = experiment
        #
        # conversion table:
        #
        self.conversion_mc_sam = {
            "mu2e": {
                # ordered to match rlc's spreadsheet...
                "fid": "file_id",

                "name": "file_name",
                "size": "file_size",
                "checksums": "checksum",
                "parents": "parents",

                "creator": "user",
                "created_timestamp": "create_date",
                "updated_by": "update_user",
                "updated_timestamp": "update_date",

                "metadata:dh.type":  "file_type",
                "metadata:dh.status":  "content_status",

                "metadata:rs.runs":          "runs",

                "metadata:dh.dataset":       "dh.dataset",
                "metadata:fn.tier":          "data_tier",
                "metadata:fn.owner":         "dh.owner",
                "metadata:fn.description":   "dh.description",
                "metadata:fn.configuration": "dh.configuration",
                "metadata:fn.sequencer":     "dh.sequencer",
                "metadata:fn.format":        "file_format",

                "metadata:rs.first_run":     "dh.first_run_subrun",
                "metadata:rs.last_run":      "dh.last_run_subrun",
                "metadata:rs.first_subrun":  "dh.first_subrun",
                "metadata:rs.last_subrun":   "dh.last_subrun",
                "metadata:rse.first_run":    "dh.first_run_event",
                "metadata:rse.last_run":     "dh.last_run_event",
                "metadata:rse.first_subrun": "dh.first_subrun_event",
                "metadata:rse.last_subrun":  "dh.last_subrun_event",
                "metadata:rse.first_event":  "dh.first_event",
                "metadata:rse.last_event":   "dh.last_event",
                "metadata:rse.nevent":       "event_count",

                "metadata:gen.count": "dh.gencount",

                "metadata:app.family":  "family",
                "metadata:app.name":    "name",
                "metadata:app.version": "version",

                # not mentioned in spreadsheet, but present in sampled files

                "metadata:job.cpu":          "job.cpu",
                "metadata:job.disk":         "job.disk",
                "metadata:job.maxres":       "job.maxres",
                "metadata:job.node":         "job.node",
                "metadata:job.site":         "job.site",
                "metadata:mc.generator_type":  "mc.generator_type",
                "metadata:mc.primary_particle":"mc.primary_particle",
                "metadata:mc.simulation_stage":"mc.simulation_stage",

            },
            "hypot": {
                "name": "file_name",
                "fid": "file_id",
                "size": "file_size",
                "checksums": "checksum",
                "parents": "parents",
                "creator": "user",
                "created_timestamp": "create_date",
                "updated_by": "update_user",
                "updated_timestamp": "update_date",

                "metadata:core.file_type":  "file_type",
                "metadata:core.content_status":  "content_status",
                "metadata:core.event_count": "event_count",

                "metadata:app.family": "family",
                "metadata:app.name":   "name",
                "metadata:app.version": "version",
                "metadata:core.runs":          "runs",
            },
            "dune": {
                "name": "file_name",
                "fid": "file_id",
                "size": "file_size",
                "checksums": "checksum",
                "parents": "parents",
                "creator": "user",
                "created_timestamp": "create_date",
                "updated_by": "update_user",
                "updated_timestamp": "update_date",

                "metadata:artdaq-core.timestamp":    "artdaq-core.timestamp",
                "metadata:artdaq-core.version":    "artdaq-core.version",
                "metadata:artdaq.timestamp":    "artdaq.timestamp",
                "metadata:artdaq.version":    "artdaq.version",
                "metadata:art.file_format_era":    "art.file_format_era",
                "metadata:art.file_format_version":    "art.file_format_version",
                "metadata:art.first_event":    "art.first_event",
                "metadata:art.last_event":    "art.last_event",
                "metadata:art.process_name":    "art.process_name",
                "metadata:art.returnstatus":    "art.returnstatus",
                "metadata:art.run_type":    "art.run_type",
                "metadata:art.variation":    "art.variation",
                "metadata:beam.momentum":    "beam.momentum",
                "metadata:beam.polarity":    "beam.polarity",
                "metadata:custom.field":    "custom.field",
                "metadata:daq.felix_status":    "daq.felix_status",
                "metadata:daq.readout":    "daq.readout",
                "metadata:data_quality.do_not_process":    "data_quality.do_not_process",
                "metadata:data_quality.is_junk":    "data_quality.is_junk",
                "metadata:data_quality.online_good_run_list":    "data_quality.online_good_run_list",
                "metadata:dataset.tag":    "dataset.tag",
                "metadata:detector.crt_status":    "detector.crt_status",
                "metadata:detector.hv_status":    "detector.hv_status",
                "metadata:detector.hv_value":    "detector.hv_value",
                "metadata:detector.pd_status":    "detector.pd_status",
                "metadata:detector.tpc_status":    "detector.tpc_status",
                "metadata:dune-artdaq.version":   "dune-artdaq.version",

                "metadata:core.file_type":          "file_type",
                "metadata:core.file_format":        "file_format",
                "metadata:core.content_status":     "content_status",
                "metadata:core.event_count":        "event_count",
                "metadata:core.first_event_number": "first_event",
                "metadata:core.last_event_number":  "last_event",
                "metadata:core.run_type":           "run_type",
                "metadata:core.runs":               "runs",
                "metadata:core.application:family": "family",
                "metadata:core.application:name":   "name",
                "metadata:core.application:version":"version",
                "metadata:dune.campaign":           "DUNE.campaign",
                "metadata:dune.creator":           "DUNE.creator",
                "metadata:dune.requestid":          "DUNE.requestid",
                "metadata:dune.DC2_production_status":"DUNE.DC2_production_status",
                "metadata:dune.production_status":  "DUNE.production_status",
                "metadata:dune_data.acCouple":  "DUNE_data.acCouple",
                "metadata:dune_data.calibpulsedac":  "DUNE_data.calibpulsedac",
                "metadata:dune_data.calibpulsemode":  "DUNE_data.calibpulsemode",
                "metadata:dune_data.comment":  "DUNE_data.comment",
                "metadata:dune_data.DAQConfigName":  "DUNE_data.DAQConfigName",
                "metadata:dune_data.detector_config":  "DUNE_data.detector_config",
                "metadata:dune_data.detector_type":  "DUNE_data.detector_type",
                "metadata:dune_data.febaselineHigh":  "DUNE_data.febaselineHigh",
                "metadata:dune.datataking":  "DUNE.datataking",
                "metadata:dune.DC2_production_status":  "DUNE.DC2_production_status",
                "metadata:dune.fcl_name":  "DUNE.fcl_name",
                "metadata:dune.fcl_path":  "DUNE.fcl_path",
                "metadata:dune.fcl_version_tag":  "DUNE.fcl_version_tag",
                "metadata:dune.generators":  "DUNE.generators",
                "metadata:dune.np02_createdate":     "DUNE.np02_createdate",
                "metadata:dune.poms_campaign_id":     "DUNE.poms_campaign_id",
                "metadata:dune.production_status":     "DUNE.production_status",
                "metadata:dune-raw-data.timestamp":     "dune-raw-data.timestamp",
                "metadata:dune-raw-data.version":     "dune-raw-data.version",
                "metadata:dune_data.fegain":  "DUNE_data.fegain",
                "metadata:dune_data.feleak10x":  "DUNE_data.feleak10x",
                "metadata:dune_data.feleakHigh":  "DUNE_data.feleakHigh",
                "metadata:dune_data.feshapingtime":  "DUNE_data.feshapingtime",
                "metadata:dune_data.inconsistent_hw_config":  "DUNE_data.inconsistent_hw_config",
                "metadata:dune_data.is_fake_data":  "DUNE_data.is_fake_data",
                "metadata:dune_data.name":  "DUNE_data.name",
                "metadata:dune_data.readout_window":  "DUNE_data.readout_window",
                "metadata:dune_data.run_mode":  "DUNE_data.run_mode",

                "metadata:dune_mc.beam_energy":    "DUNE_MC.beam_energy",
                "metadata:dune_mc.beam_flux_ID":    "DUNE_MC.beam_flux_ID",
                "metadata:dune_mc.beam_polarity":    "DUNE_MC.beam_polarity",
                "metadata:dune_mc.detector_type":    "DUNE_MC.detector_type",
                "metadata:dune_mc.electron_lifetime":    "DUNE_MC.electron_lifetime",
                "metadata:dune_mc.generators":    "DUNE_MC.generators",
                "metadata:dune_mc.generators_version":    "DUNE_MC.generators_version",
                "metadata:dune_mc.gen_fcl_filename":    "DUNE_MC.gen_fcl_filename",
                "metadata:dune_mc.geometry_version":    "DUNE_MC.geometry_version",
                "metadata:dune_mc.liquid_flow":    "DUNE_MC.liquid_flow",
                "metadata:dune_mc.mass_hierarchy":    "DUNE_MC.mass_hierarchy",
                "metadata:dune_mc.miscellaneous":    "DUNE_MC.miscellaneous",
                "metadata:dune_mc.mixerconfig":    "DUNE_MC.mixerconfig",
                "metadata:dune_mc.name":    "DUNE_MC.name",
                "metadata:dune_mc.neutrino_flavors":    "DUNE_MC.neutrino_flavors",
                "metadata:dune_mc.oscillationP":    "DUNE_MC.oscillationP",
                "metadata:dune_mc.overlay":    "DUNE_MC.overlay",
                "metadata:dune_mc.readout_time":    "DUNE_MC.readout_time",
                "metadata:dune_mc.space_charge":    "DUNE_MC.space_charge",
                "metadata:dune_mc.TopVolume":    "DUNE_MC.TopVolume",
                "metadata:dune_mc.trigger-list-version":    "DUNE_MC.trigger-list-version",
                "metadata:dune_mc.with_cosmics": "DUNE_MC.with_cosmics",
                "metadata:info.cpusec":     "info.cpusec",
                "metadata:info.creator":     "info.creator",
                "metadata:info.memory":     "info.memory",
                "metadata:info.physicsgroup":     "info.physicsgroup",
                "metadata:info.wallsec":     "info.wallsec",
                "metadata:lbne_data.detector_type":     "lbne_data.detector_type",
                "metadata:lbne_data.name":     "lbne_data.name",
                "metadata:lbne_data.run_mode":     "lbne_data.run_mode",
                "metadata:lbne_mc.beam_energy":     "lbne_MC.beam_energy",
                "metadata:lbne_mc.beam_flux_ID":     "lbne_MC.beam_flux_ID",
                "metadata:lbne_mc.detector_type":     "lbne_MC.detector_type",
                "metadata:lbne_mc.generators":     "lbne_MC.generators",
                "metadata:lbne_mc.geometry_version":     "lbne_MC.geometry_version",
                "metadata:lbne_mc.mass_hierarchy":     "lbne_MC.mass_hierarchy",
                "metadata:lbne_mc.miscellaneous":     "lbne_MC.miscellaneous",
                "metadata:lbne_mc.name":     "lbne_MC.name",
                "metadata:lbne_mc.neutrino_flavors":     "lbne_MC.neutrino_flavors",
                "metadata:lbne_mc.oscillationP":     "lbne_MC.oscillationP",
                "metadata:lbne_mc.horncurrent":     "lbne_MC.HornCurrent",
                "metadata:lbne_mc.production_campaign":     "lbne_MC.production_campaign",
                "metadata:lbne_mc.trigger-list-version":     "lbne_MC.trigger-list-version",
                "metadata:mc.liquid_flow": "MC.liquid_flow",
                "metadata:mc.readout_time": "MC.readout_time",
                "metadata:mc.space_charge": "MC.space_charge",
                "metadata:mc.with_cosmics": "MC.with_cosmics",
                "metadata:neardetector_mc.offaxisposition": "NearDetector_MC.OffAxisPosition",
                "metadata:online.category": "Online.Category",
                "metadata:online.daq_config": "Online.daq_config",
                "metadata:online.daq_host": "Online.daq_host",
                "metadata:online.runnumber": "Online.RunNumber",
                "metadata:online.run": "Online.Run",
                "metadata:online.subrun": "Online.Subrun",
                "metadata:online.timestamp": "Online.Timestamp",
                "metadata:online.triggerconfig": "Online.triggerconfig",
                "metadata:online.triggertype": "Online.triggertype",
                "metadata:POMS.CAMPAIGN_ID": "POMS.CAMPAIGN_ID",
                "metadata:POMS.CAMPAIGN_STAGE_ID": "POMS.CAMPAIGN_STAGE_ID",
                "metadata:POMS.SUBMISSION_ID": "POMS.SUBMISSION_ID",
            }
        }
        self.build_inverse()


    def build_inverse(self):
        """ build the inverse mapping from the forward one"""
        self.conversion_sam_mc = {}
        for k in self.conversion_mc_sam:
            self.conversion_sam_mc[k] = {}
            for k2 in self.conversion_mc_sam[k]:
                v = self.conversion_mc_sam[k][k2]
                self.conversion_sam_mc[k][v] = k2



    def convert_all_sam_mc(self,md, namespace):
        res = {"namespace": namespace, "metadata":{}}
        for k, v in md.items():
            if not k in self.conversion_sam_mc[self.experiment]:
                continue
            # most things need no conversion, except...
            converter = convert_noop
            if k == "file_id":
                converter = str 
            if k == "checksum":
                converter = convert_checksums_sam_mc
            if k == "parents":
                converter = convert_parents_sam_mc
            if k == "runs":
                converter = convert_runs_sam_mc
            if k in [ "create_date", "update_date"]:
                converter = convert_date_sam_mc
            # in metacat, some things are in the metadata sub-dictionary
            # in this case the conversion key starts with metadata:
            ck = self.conversion_sam_mc[self.experiment][k]
            if ck.startswith("metadata:"):
                ck = ck.replace("metadata:","")
                res["metadata"][ck] = converter(v)
            else:
                res[ck] =  converter(v)

        return res

    def convert_all_mc_sam(self, md):
        res = {}
        for k, v in md.items():
            if not k in self.conversion_mc_sam[self.experiment]:
                continue
            ck = self.conversion_mc_sam[self.experiment][k]
            # most keys don't require conversion, except...
            converter = convert_noop
            if k == "fid":
               # cannot generally convert metacat fids to SAM integer file ids..
               continue
            if k == "parents":
                converter = convert_parents_mc_sam
            if k == "checksums":
                converter = convert_checksums_mc_sam
            if k in [ "created_timestamp", "updated_timestamp" ]:
                converter = convert_date_mc_sam
            res[ck] = converter(v, md)
        # some things are in the metadata sub-dictionary...
        # they are listed as metadata:x in the table
        for k, v in md["metadata"].items():
            converter = convert_noop
            if not ("metadata:"+k) in self.conversion_mc_sam[self.experiment]:
                continue
            ck = self.conversion_mc_sam[self.experiment]["metadata:"+k]
            if ck == "runs":
                converter = convert_runs_mc_sam
            if not ck == "run_type":
                res[ck] = converter(v, md)
        return res

