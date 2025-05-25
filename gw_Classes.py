##############################################################
#
#   myclasses.py
#
#   Containes following user defined classes:
#       myError
#       mySignals
# 
##############################################################
import traceback

class myError:

    def __init__(self, error, location='unknown'):
        """
        Data object to capture try / except data

        example:

        try:
            <some code>
        except Exception as <error>:
            myerr = myError(<error>)     # create instance
            
        
        optional
            err.location = <text> to indicate where in code Exception occurred

        Requires traceback module

        """
        self.error = error
        self.type = type(error).__name__
        self.name = error.args[0]
        self.traceback = traceback.format_exc()
        self.location = location    # optional description of where error occurred

        print('At myError ...\n')
        print("Error Type: ", self.type)
        print("Error Name:", self.name)
        print("Error Location:", self.location)
        print(self.traceback)

class gwColors:             # data class of text colors 
    """
    Data object defines text colors for gw_web
    """

    def __init__(self):
        self.blink = '\033[5m'	    # escape sequence for blink
        self.reset = '\033[0m'	    # escape sequence to RESET text
        
        self.bred = '\033[1;31m'	# escape sequence for BOLD red
        self.byellow = '\033[1;33m'	# escape sequence for BOLD yellow
        self.bwhite = '\033[1;37m'  # escape sequence for BOLD white
        self.bgreen = '\033[1;32m'  # escape sequence for BOLD green
        self.bcyan = '\033[1;36m'   # escape sequence for BOLD cyan
        
        self.red = '\033[0;31m'	    # escape sequence for red
        self.yellow = '\033[0;33m'	# escape sequence for yellow
        self.white = '\033[0;37m'   # escape sequence for white
        self.green = '\033[0;32m'   # escape sequence for green
        self.cyan = '\033[0;36m'    # escape sequence for cyan


class mySignals:            # data class of signals for gw_web
    """
    Data object defines signals for gw_web
    """
    def __init__(self):
        self.Open = "60"
        self.Closed = "61"
        self.Opening = "62"
        self.Closing = "63"


