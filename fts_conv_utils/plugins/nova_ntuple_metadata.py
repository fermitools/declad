
import json
import fts.util
import fts.metadata_extractors

import re,sys,json,os,os.path

class NovaNTuple(fts.metadata_extractors.MetadataExtractorRunCommand):
  name = "nova-ntuple"
  _concurrent_limit = 2

  def getMetadataFile(self, filestate):
    jsonName = filestate.getLocalFilePath()

    if not '.root' in jsonName: return
    jsonName = jsonName.replace('.root', '.json')

    exists = self._checkmdfile(jsonName, filestate)
    if not exists: return
    return jsonName

  def extract(self, filestate, *args, **kwargs):
    group = 'nova'
    try:
      jsonfilename = self.getMetadataFile(filestate)
      if jsonfilename:
        md = json.load(open(jsonfilename))
        return md
    except Exception as e:
      print(e)
      print("Exception reading json file")


extractor = NovaNTuple()
