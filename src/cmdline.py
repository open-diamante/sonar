# -*- coding: utf-8 -*-
__author__      = "Brian Fromme"
__copyright__   = "Copyright 2020, Gnu Public License - Version 2.0"
__credits__     = ["Brian Fromme, Bryan Gartner, Darren Soothill"]
__maintainer__  = "Brian Fromme"
__status__      = "Prototype"
__version__     = "0.1"
## NOTE: __version__  Is this really where we want to define the program version number?
"""
@newfield description: Description
"""
__description__ = "Sonar command-line parsing"

import sys
import argparse


class Options:
   """base class for command-line options"""
   exiting = False   # set to true to disable class destruction warning

   def __init__(self):
      self.argInput = 'sonar-input.yaml'
      self.argOutput = 'sonar-results.out'
      self.argVerbose = False
      self.argDebug = False
      self.argVersion = '%(prog)s 0.1'   # not ideal
      'Setup the argparse object with our options'
      self.parser = argparse.ArgumentParser(description='SST: Sonar Sizing Tool options.')
      # options without parameters
      self.parser.add_argument('--version', action='version', version=self.argVersion)
      self.parser.add_argument('--debug', action='store_true', help="turn on debugging")
      self.parser.add_argument('--verbose', action='store_true', help="increase output verbosity")
      # options with parameters
      self.parser.add_argument('-i', '--input', default=self.argInput, help='yaml input file (default: sonar-input.yaml)')
      self.parser.add_argument('-o', '--output', default=self.argOutput, help='printed output file (default: sonar-results.out)')

   def __del__(self):
      classless_name = self.__class__.__name__
      if not self.exiting and self.argDebug:
          print (classless_name, f'instance destroyed. You must not del the {classless_name} instance except upon exit.', file=sys.stderr)

   def displayFiles(self):
      if self.argVerbose:
         print (f'Input File: {self.argInput}', file=sys.stdout)
         print (f'Output File: {self.argOutput}', file=sys.stdout)

   def parseCommandLine(self):
      """Run the argparse parsing method"""
      args = self.parser.parse_args()
      if args.debug:
         self.argDebug = True
      if args.verbose:
         self.argVerbose = True
      # While these might seem redundant, need to set the parsed input and output values back to our instance
      self.argInput = args.input
      self.argOutput = args.output

