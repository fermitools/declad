from twisted.internet import defer
from twisted.python import log
import sys

import fts.util
import fts.metadata_extractors

import re,sys,json,os
import unicodedata



def hasJson(jStr):
    return "{" in jStr or "[" in jStr

def loads_recursive(jStr):
    j = json.loads(str(jStr))

    # occasionally values get passed as ints and it breaks things,
    # ensure they're cast as strings
    for key, value in j.items():
        if type(value) == int:
            j[key]=str(value)

    try:
        # If this works, it's a dict
        return { key:(loads_recursive(value) if hasJson(value) else value) for key, value in j.items() }
    except:
        # Otherwise it's a list
        return [loads_recursive(item) if hasJson(item) else item for item in j]



class NovaCAFExtractor(fts.metadata_extractors.MetadataExtractorRunCommand):
    name = "nova-caf"
    _concurrent_limit = 4
    group = 'nova'

    def extract( self, filestate, *args, **kwargs):
        # find the executable on the path
        deferred = self._runCommand("extractCAFMetadata", filestate.getLocalFilePath())
        group = 'nova'
        deferred.addCallback(self._createMetadata)
        return deferred

    def _createMetadata(self, output):
        # strip out anything before the first "{" character so that the json can be decoded
        output = output[output.find("{"):]
        try:
            md = loads_recursive(output)
        except:
            log.msg('Something wrong with the JSON extracted from this file?')
            log.msg(output[0:10000]) # truncate for safety
            raise

        md['group'] = self.group
        return md

novaCAFExtractor = NovaCAFExtractor()
