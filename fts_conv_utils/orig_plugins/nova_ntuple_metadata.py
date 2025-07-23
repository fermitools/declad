from twisted.internet import defer
from twisted.python import log

import json
import fts.util
import fts.metadata_extractors

import re,sys,json,os,os.path

class NovaNTuple(fts.metadata_extractors.MetadataExtractorRunCommand):
  name = "nova-ntuple"
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
  def extract(self, filestate, *args, **kwargs):
    group = 'nova'
    try:
      jsonfilename = yield self.getMetadataFile(filestate)
      if jsonfilename:
        md = json.load(open(jsonfilename))
        defer.returnValue(md)
    except Exception as e:
      print(e)
      print("Exception reading json file")


novaNTupleExtractor = NovaNTuple()
