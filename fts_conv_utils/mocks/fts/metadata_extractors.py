import os

class Command_value:
    def __init__(self, output ):
        self._output = output

    def addCallback(self, f):
        self._output = f(self._output)
        return self

class MetadataExtractorRunCommand:
    def _runCommand(self, *args):
        full_cmd = ' '.join(args)
        print(f"running: {full_cmd}")
        with os.popen(full_cmd) as cmdout:
             res = cmdout.read()
        #return Command_value(res)
        return res
