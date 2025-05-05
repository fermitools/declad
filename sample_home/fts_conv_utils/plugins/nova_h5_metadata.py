# Extract the metadata for HDF5 files.

from twisted.internet import defer, threads
from twisted.python import log

import fts.util
import fts.metadata_extractors
import h5py
import re,sys,json,os,os.path

import MetadataUtils

def _createMetadata(filename, group, filesizebytes):
    md = {'file_name': filename, 'group':group, 'file_size': filesizebytes}

    md['data_tier'] = unicode('h5')

    return md

class NovaH5(fts.metadata_extractors.MetadataExtractorRunCommand):
    name = "nova-h5"
    _concurrent_limit = 4

    @defer.inlineCallbacks
    def getMetadataFile(self, filestate):
        jsonName = filestate.getLocalFilePath()

        if not '.h5' in jsonName: return
        jsonName = jsonName.replace('.h5', '.json')

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
            print e
            print 'Exception reading json file, falling back to direct extraction'

        # find the executable on the path
        md = _createMetadata(filestate.getFileName(), group, filestate.getFileSize())
        defer.returnValue(md)

novaH5Extractor = NovaH5()
