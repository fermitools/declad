# Extract the metadata for text files from the file name

from twisted.internet import defer, threads
from twisted.python import log

import fts.util
import fts.metadata_extractors

import re,sys,json,os,os.path


def _createMetadata(filename, group, filesizebytes):
    md = {'file_name': filename, 'group':group, 'file_size': filesizebytes}

    md['file_type'  ] = "text"
    md['file_format'] = "text"
    md['TextFileList.ParentDefinition'] = re.search('FileList_(.+?)_SnapID' , filename).group(1)
    md['TextFileList.ParentSnapshotID'] = re.search('SnapID-(.+?)_TotRuns'  , filename).group(1)
    md['TextFileList.TotalRuns']        = re.search('TotRuns-(.+?)_FirstRun', filename).group(1)
    md['TextFileList.FirstRun']         = re.search('FirstRun-(.+?)_LastRun', filename).group(1)
    md['TextFileList.LastRun']          = re.search('LastRun-(.+?)_TotFiles', filename).group(1)
    md['TextFileList.TotalFiles']       = re.search('TotFiles-(.+?)_Time'   , filename).group(1)
    md['TextFileList.TimeStamp']        = re.search('Time-(.+?).txt'        , filename).group(1)

    return md

class NovaText(fts.metadata_extractors.MetadataExtractorRunCommand):
    name = "nova-text"
    _concurrent_limit = 4

    @defer.inlineCallbacks
    def getMetadataFile(self, filestate):
        jsonName = filestate.getLocalFilePath()

        if not '.txt' in jsonName: return
        jsonName = jsonName.replace('.txt', '.json')

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
                md = _createMetadata(filestate.getFileName(), group, filestate.getFileSize())
                log.msg("Using metadata file %s for %s" % (jsonfilename, filestate.getFileName()))
                if md:
                    defer.returnValue(md)

        except Exception as e:
            print(e)
            print('Exception reading json file, falling back to direct extraction')

        # find the executable on the path
        md = _createMetadata(filestate.getFileName(), group, filestate.getFileSize())
        defer.returnValue(md)

novaTextExtractor = NovaText()
