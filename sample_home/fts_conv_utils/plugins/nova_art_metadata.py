# Extract the metadata from the output of sam_metadata_dumper

from twisted.internet import defer, threads
from twisted.python import log

import fts.util
import fts.metadata_extractors

import re,sys,json,os,os.path


def unCamelCase(s):
    """ Convert CamelCase to camel_case """

    # \B matches an empty string which is NOT at the beginning of a word
    # so requiring this means no _ will be inserted at the start

    return re.sub( r'\B([A-Z])', r'_\1', s).lower()


def _createMetadata(data, filename, group, filesizebytes):
    md = {'file_name': filename, 'group':group, 'file_size': filesizebytes}

    # If have a transpose file force the PlaneNumber into the metadata
    if "outplane" in filename:
      try:
        plane = re.search('^.*outplane(\d*).pclist.root', filename).group(1)
        print( "Plane number:", plane, ". Is a transpose file")
        md['Calibration.PlaneNumber'] = plane
      except:
        print( "No plane number found in transpose file")

    dumperDict = json.loads(data)

    for dumperKey in dumperDict:
        if str(filename) in str(dumperKey):
            tmpMD = dumperDict[dumperKey]

            for k,v in tmpMD.iteritems():
                if '.' not in k:
                    k = unCamelCase(k)
                else:
                    k.lower()
                    v = str(v)

                if k == 'parents':
                    #parents contains a list, either of ints, strings, or dictionaries with "file_name" and "file_id" as keys
                    vTmp = []
                    for entry in v:
                        if isinstance(entry, int):
                            pass
                        elif isinstance(entry, basestring):
                            entry = os.path.basename(entry)
                            if entry.endswith('sim.g4.root'):
                                entry = re.sub( r'sim.g4.root$', r'fcl', entry )
                        elif isinstance(entry, dict):
                            if "file_name" in entry:
                                entry["file_name"] = os.path.basename( entry["file_name"] )
# Types are incorrect here, and we've never actually run with this code. If
# it's needed it should be fixed before being uncommented.
#                                if entry.endswith('sim.g4.root'):
#                                    entry = re.sub( r'sim.g4.root$', r'fcl', entry )
                        vTmp.append(entry)
                    v = vTmp

                if k == 'process_name' and md.get('application',[]).get('name') is None:
                    k = 'application_name'
                elif k == 'stream_name':
                    k = 'data_stream'

                if k in ('start_date', 'end_date'):
                    v = long(v)

                if k in ('first_event', 'last_event', 'art.first_event', 'art.last_event'):
                    try:
                        v = int(v)
                    except (TypeError, ValueError):
                        if len(v) == 3:
                            v = v[2]
                        else:
                            continue

                if k.startswith('application_'):
                    if 'application' not in md:
                        md['application'] = {}
                    md['application'][k[12:]] = v
                elif k in ('file_format_era', 'file_format_version'):
                    pass
                else:
                    md[k] = v

    ### HACKETTY HACK HACK For Calib Transpose
    if "outplane" in md['data_stream']:
        md['data_stream'] = "outpclist"

    return md

class NovaArt(fts.metadata_extractors.MetadataExtractorRunCommand):
    name = "novaart"
    #_concurrent_limit = 4
    _concurrent_limit = 2

    @defer.inlineCallbacks
    def getMetadataFile(self, filestate):
        jsonName = filestate.getLocalFilePath()

        if not '.root' in jsonName: return
        jsonName = jsonName.replace('.root', '.json')

        exists = yield self._checkmdfile(jsonName, filestate)
        if not exists: return
        defer.returnValue(jsonName)

    @defer.inlineCallbacks
    def extract( self, filestate, *args, **kwargs):
        group = 'nova'
        try:
            jsonfilename = yield self.getMetadataFile(filestate)
            if jsonfilename:
                jsonfile = yield threads.deferToThread(open, jsonfilename)
                try:
                    mddata = yield threads.deferToThread(jsonfile.read)
                finally:
                    yield threads.deferToThread(jsonfile.close)
                md = _createMetadata(mddata, filestate.getFileName(), group, filestate.getFileSize())
                log.msg("Using metadata file %s for %s" % (jsonfilename, filestate.getFileName()))
                if md:
                    defer.returnValue(md)

        except Exception as e:
            print( e)
            print( 'Exception reading json file, falling back to direct extraction')

        # find the executable on the path
        mddata = yield self._runCommand("sam_metadata_dumper", filestate.getLocalFilePath())
        md = _createMetadata(mddata, filestate.getFileName(), group, filestate.getFileSize())
        defer.returnValue(md)

novaArtExtractor = NovaArt()
