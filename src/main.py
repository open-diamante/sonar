# -*- coding: utf-8 -*-
__author__      = "Brian Fromme"
__copyright__   = "Copyright 2020, Gnu Public License - Version 2.0"
__credits__     = ["Brian Fromme, Bryan Gartner, Darren Soothill"]
__maintainer__  = "Brian Fromme"
__status__      = "Prototype"
"""
@newfield description: Description
"""
__description__ = "Sonar main module"

import os
# our classes
from cmdline import Options
from sizingdata import SizingData


def main():
    opts = Options()
    # read the command-line options and print the file names
    opts.parseCommandLine()
    opts.displayFiles()

    sizingData = SizingData(opts)
    # read the yaml input and validate the input
    if sizingData.readYAMLInput():
        sizingData.validateSizingData()
        if (opts.argDebug):
            # print it back out
            sizingData.printSizingData()
        sizingData.calculateResults()
        sizingData.reportSizingResults()

    opts.exiting = True


if __name__ == "__main__":
    main()

