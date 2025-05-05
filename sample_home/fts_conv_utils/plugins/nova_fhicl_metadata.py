from twisted.internet import defer
from twisted.python import log

import fts.util
import fts.metadata_extractors

import re,sys,json,os

class NovaFhclExtractor(fts.metadata_extractors.MetadataExtractorRunCommand):
    name = "nova-fhcil"
    _concurrent_limit = 4
    group = 'nova'

    def extract( self, filestate, *args, **kwargs):

        # find the executable on the path
        deferred = self._runCommand("parseFCLMetadata", filestate.getLocalFilePath())
        group = 'nova'
        deferred.addCallback(self._createMetadata)
        return deferred

    def _createMetadata(self, output):
        md = json.loads(output)
        md['group'] = self.group
        return md

novaFHCILExtractor = NovaFhclExtractor()
