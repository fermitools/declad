
class Command_value:
    def __init__(self, output ):
        self._output = output

    def addCallback(self, f):
        self._output = f(self._output)
        return self

class MetadataExtractorRunCommand:
    def _runCommand(cmd, arg):
        with os.popen(f"{cmd} {arg}") as cmdout:
             res = cmdout.read()
        return Command_value(res)
