from twisted.internet import defer, task, reactor
from twisted.python import log
import sys
import time

import fts.util
import fts.sam
import fts.filestate
import fts.metadata_extractors

import re,sys,json,os
import unicodedata

class NovaLogExtractor(fts.metadata_extractors.MetadataExtractorRunCommand):
  name = "nova-log"
  _concurrent_limit = 4
  group = 'nova'

  @defer.inlineCallbacks
  def extract( self, filestate, *args, **kwargs):
    logName = os.path.basename(filestate.getLocalFilePath())
    if logName.endswith('.log'):
      rootName = logName.replace('.log', '.root')
    if logName.endswith('.log.bz2'):
      rootName = logName.replace('.log.bz2', '.root')

    starttime = time.time()
    while True:
        if rootName in fts.filestate.failedFiles:
            raise fts.metadata_extractors.MetadataExtractError("%s needs parent %s, but it is in failed state" % (logName, rootName))
        rootFile = fts.filestate.allFiles.getFile(rootName)
	if rootFile:
            states = rootFile.getStates()
            for s in states:
                if isinstance(s, fts.filestate.NewFileState):
                    break # probably not declared - need to wait
            else:
                break # file should be available
        else:
            # really want to check if the file is in the db, but fts.sam doesn't
            # provide a suitable interface
            locs = yield fts.sam.getLocations(rootName)
            if locs is not None: break
        if time.time() > starttime + 3600*6:
            raise fts.metadata_extractors.MetadataExtractError("%s needs parent %s, but it is not in the SAM DB" % (logName, rootName))
        filestate.setStatus("Waiting for parent %s to be added to DB" % rootName)
        # sleep
        yield task.deferLater(reactor, 900, lambda: None)

    defer.returnValue( {
      'file_name': logName,
      'data_tier': 'log',
      'file_format': 'log',
      'file_type': 'unknown', # maybe 'nonPhysicsGeneric'?
      'file_size': filestate.getFileSize(),
      'parents': [{'file_name': rootName}]
    } )

novaLogExtractor = NovaLogExtractor()
