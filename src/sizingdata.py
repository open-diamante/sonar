# -*- coding: utf-8 -*-
__author__      = "Brian Fromme"
__copyright__   = "Copyright 2020, Gnu Public License - Version 2.0"
__credits__     = ["Brian Fromme, Bryan Gartner, Darren Soothill"]
__maintainer__  = "Brian Fromme"
__status__      = "Prototype"
"""
@newfield description: Description
"""
__description__ = "Sonar sizing data - obtained from user input"

import math
import os.path
import sys
import yaml

from cmdline import Options


class SizingData:
    """base class for SST user input data - various input methods will be defined here"""

    # Constants: These are defined by SUSE architects. Consider these in computations below.
    SDCONST_COLOMEMORY = 32
    SDCONST_MEM2DRIVES = 5
    SDCONST_MEMEXTRA = 16
    SDCONST_COLOCPUS = 8
    SDCONST_COLOMAXNODES = 15
    SDCONST_SSD2THREAD = 2
    SDCONST_MINTHREADS = 32
    SDCONST_4215R = 'Xeon 4215r'
    SDCONST_6248R = 'Xeon 6248r'
    SDCONST_NVMEFACTOR = 68
    SDCONST_HDDFACTOR = 35
    SDCONST_GBS = 1000
    SDCONST_SSDFACTOR = 120
    SDCONST_NVMEFACTOR = 300

    def __init__(self, optionsInstance):
        'The caller must pass us the Options instance - for command line options'
        self.options = optionsInstance
        self.sizingData = None
        ### Input Values
        # Co-Location of Gateway/MDS/MON's        Yes
        # Use Case                                Archive|Mixed
        # Capacity Required (TB)                  2000
        # Metadata Capacity (TB)
        # Drive Capacity (TB)                     16
        # Number of drives per Chassis            24
        # Number of Populated slots per Chassis   24
        # Number of NVME Slots per Chassis        6
        # Drive Types                             HDD|SSD
        # Max Fill Capacity %                     80
        # NVME Ratio 1:                           12
        # Protection Type (EC=1 OR: num from 2-6   1
        # EC Profile Data                          8
        # EC Profile Parity                        3
        ## NOTE: all of these default values are completely fictitious, which is why input validation is crucial
        self.sdi_Colo = True
        self.sdi_ArchiveUseCase = True
        self.sdi_StorageCapacity = 2000
        self.sdi_MetaDataCapacity = 0
        self.sdi_DriveCapacity = 16
        self.sdi_DrivesPerChassis = 24
        self.sdi_PopulatedSlotsPerChassis = 24
        self.sdi_NVMeSlotsPerChassis = 6
        self.sdi_DriveTypeSSD = False
        self.sdi_MaxFillCapacityPercent = 80
        self.sdi_NVMeRatio = 12
        self.sdi_ProtectionType = 1
        self.sdi_ECData = 8
        self.sdi_ECParity = 3
        # computed total parity
        self.sdc_ECProfile = self.sdi_ECData + self.sdi_ECParity
        # This tells us whether there were computational errors
        self.sdc_ComputationalErrors = False

    def calculateResults(self):
        ### Calculations -> Results
        # Raw capacity required (TB): sdStorageCapacity / (sdMaxFillCapacityPercent*100)
        #     NOTE: compute this value first, as the Total capacity depends upon this result
        self.sdr_RawCapacity = self.sdi_StorageCapacity / (self.sdi_MaxFillCapacityPercent*100)
        # Total capacity (TB): 
        if self.sdi_ProtectionType == 1:
            self.sdr_TotalCapacity = (self.sdr_RawCapacity / self.sdi_ECData) * (self.sdi_ECData + self.sdi_ECParity)
        else:
            self.sdr_TotalCapacity = self.sdr_RawCapacity * self.sdi_ProtectionType
        # Number of drives needed: 
        self.sdr_DrivesNeeded = math.ceil(self.sdr_TotalCapacity / self.sdi_DriveCapacity)
        # Number of chassis needed: 
        # =IF(B19<>"EC",ROUNDUP((B26/B13),0),IF(B21+C21<B26/B13,ROUNDUP((B26/B13),0),"Number of nodes too low for EC profile"))
        self.sdc_ChassisEstimate = math.ceil(self.sdr_DrivesNeeded / self.sdi_PopulatedSlotsPerChassis)
        if self.sdi_ProtectionType == 1:
            if self.sdc_ECProfile < self.sdc_ChassisEstimate:
                self.sdr_ChassisNeeded = self.sdc_ChassisEstimate
            else:
                # error: Number of nodes too low for EC profile
                self.sdr_ChassisNeeded = 0
                print("Number of nodes too low for EC profile", file=sys.stderr)
                self.sdc_ComputationalErrors = True
        else:
            self.sdr_ChassisNeeded = self.sdc_ChassisEstimate
        # Colo memory needed: 
        self.sdr_ColoMemoryNeeded = (self.SDCONST_COLOMEMORY if self.sdi_Colo else 0)
        # Minimum memory needed: 
        self.sdr_MinimumMemoryNeeded = self.sdi_DrivesPerChassis * self.SDCONST_MEM2DRIVES + self.SDCONST_MEMEXTRA + self.sdr_ColoMemoryNeeded
        # Colo CPU needed: 
        self.sdr_ColoCPUNeeded = (self.SDCONST_COLOCPUS if self.sdi_Colo else 0)
        # Number of 2Ghz CPU threads per chassis needed: 
        self.sdr_ColoThreadsNeeded = (self.sdi_DrivesPerChassis * self.SDCONST_SSD2THREAD if self.sdi_DriveTypeSSD else self.sdi_DrivesPerChassis)
        # Suggested CPU model: 
        self.sdr_SuggestedCPU = (self.SDCONST_4215R if (self.sdr_ColoCPUNeeded+self.sdr_ColoThreadsNeeded)<self.SDCONST_MINTHREADS else self.SDCONST_6248R)
        # Number of NVMe devices needed for RocksDB/WAL: 
        self.sdr_NVMeNeeded = math.ceil(self.sdi_DrivesPerChassis / self.sdi_NVMeRatio)
        # Minimum size of NVMe devices (GB): 
        self.sdr_MinimumNVMeSize = math.ceil((self.sdi_DrivesPerChassis*self.SDCONST_NVMEFACTOR) / self.sdr_NVMeNeeded)
        # Expected performance (GB/s): 
        self.sdr_ExpectedPerfGBs = ((self.sdr_DrivesNeeded*self.SDCONST_SSDFACTOR)/self.SDCONST_GBS if self.sdi_DriveTypeSSD else (self.sdr_DrivesNeeded*self.SDCONST_HDDFACTOR)/self.SDCONST_GBS)
        # Network cards:  TBD
        self.sdr_NetworkCards = 'Not Implemented'

        ### Calculations -> BOM
        # Number of chassis - Zero represents an error condition
        self.sdr_BOM_NumberOfChassis = 0
        if self.sdi_Colo and self.sdr_ChassisNeeded > self.SDCONST_COLOMAXNODES:
            # Error - too many chassis
            print(f'Number of nodes ({self.sdr_ChassisNeeded}) is too high for co-location', file=sys.stderr)
            self.sdc_ComputationalErrors = True
        else:
            self.sdr_BOM_NumberOfChassis = self.sdr_ChassisNeeded
        # Number of drives per chassis and their capacity (just what we were told from input) (in TB)
        self.sdr_BOM_DrivesPerChassis = self.sdi_DrivesPerChassis
        self.sdr_BOM_DriveSize = self.sdi_DriveCapacity
        # Memory per chassis (in GB)
        self.sdr_BOM_MemoryPerChassis = self.sdr_MinimumMemoryNeeded
        # CPU per chassis (2 of)
        self.sdr_BOM_CPUPerChassis = self.sdr_SuggestedCPU
        # RocksDB/WAL (NMVe)
        self.sdr_BOM_NVMe = self.sdr_NVMeNeeded
        self.sdr_BOM_NVMeSize = self.sdr_MinimumNVMeSize
        # OS Disk
        self.sdr_BOM_OSDisk = 'Not Implemented'
        # Metadata NVMEs
        self.sdr_BOM_MetaDataNVMes = 'Not Implemented'
        # Network Cards
        self.sdr_BOM_OSDisk = 'Not Implemented'
        ## End of Calculation and BOM variables
        ## NOTE: Still need to implement a BOM for the Admin Node

        # return True, unless an error occurred
        return not self.sdc_ComputationalErrors

    def reportSizingResults(self):
        """Report the sizing results we computed from the user input"""
        if self.sizingData is None:
            print (f'Error: No yaml input: {self.options.argInput}', file=sys.stderr)
            return False
        else:
            print()
            print(f'Sizing First-Opinion:')
            print(f'Raw Capacity = {self.sdr_RawCapacity}')
            # Total capacity (TB): 
            print(f'Total Capacity = {self.sdr_TotalCapacity}')
            # Number of drives needed: 
            print(f'Number of Drives = {self.sdr_DrivesNeeded}')
            # Number of chassis needed: 
            print(f'Number of Chassis = {self.sdr_ChassisNeeded}')
            # Colo memory needed: 
            print(f'Colocated Memory Needed = {self.sdr_ColoMemoryNeeded}')
            # Minimum memory needed: 
            print(f'Minimum Memory Needed = {self.sdr_MinimumMemoryNeeded}')
            # Colo CPU needed: 
            print(f'Colocated CPU Needed = {self.sdr_ColoCPUNeeded}')
            # Number of 2Ghz CPU threads per chassis needed: 
            print(f'Number of 2Ghz CPU Threads Needed = {self.sdr_ColoThreadsNeeded}')
            # Suggested CPU model: 
            print(f'Suggested CPU Model = {self.sdr_SuggestedCPU}')
            # Number of NVMe devices needed for RocksDB/WAL: 
            print(f'Number of NVMe Devices Needed for RocksDB/WAL = {self.sdr_NVMeNeeded}')
            # Minimum size of NVMe devices (GB): 
            print(f'Minimum Size of NVMe Devices = {self.sdr_MinimumNVMeSize}')
            # Expected performance (GB/s): 
            print(f'Expected Performance (GB/s) = {self.sdr_ExpectedPerfGBs}')
            # Network cards:  TBD
            print(f'Network Cards = {self.sdr_NetworkCards}')

            ### Calculations -> BOM
            print()
            print(f'BOM First-Opinion:')
            # Number of chassis - Zero represents an error condition
            print(f'Number of Chassis = {self.sdr_BOM_NumberOfChassis}')
            # Number of drives per chassis and their capacity (just what we were told from input) (in TB)
            print(f'Number of Drives Per Chassis = {self.sdr_BOM_DrivesPerChassis}')
            print(f'Drive Size = {self.sdr_BOM_DriveSize}')
            # Memory per chassis (in GB)
            print(f'Memory Per Chassis = {self.sdr_BOM_MemoryPerChassis}')
            # CPU per chassis (2 of)
            print(f'CPU Per Chassis = {self.sdr_BOM_CPUPerChassis}')
            # RocksDB/WAL (NMVe)
            print(f'RocksDB/WAL Number of NVMe Drives = {self.sdr_BOM_NVMe}')
            print(f'RocksDB/WAL NVMe Capacity = {self.sdr_BOM_NVMeSize}')
            # OS Disk
            print(f'OS Disk Capacity = {self.sdr_BOM_OSDisk}')
            # Metadata NVMEs
            print(f'NVMe Metadata Capacity = {self.sdr_BOM_MetaDataNVMes}')
            # Network Cards
            print(f'Network Cards = {self.sdr_BOM_OSDisk}')
            ## End of Calculation and BOM variables

    def __del__(self):
        classless_name = self.__class__.__name__
        if not self.options.exiting and self.options.argDebug:
            print (f'{classless_name} instance destroyed. You must not del this instance except upon exit.', file=sys.stderr)

    def readYAMLInput(self):
        if not os.path.isfile(self.options.argInput):
            print (f'Error: Cannot find yaml input: {self.options.argInput}', file=sys.stderr)
            return False
        if self.options.argVerbose:
           print (f'Attempting to open input file: {self.options.argInput}', file=sys.stdout)
        with open(self.options.argInput, 'r') as f:
           if self.options.argVerbose:
              print (f'Reading yaml input file: {self.options.argInput}', file=sys.stdout)
           self.sizingData = yaml.safe_load(f)
        # NOTE: What about yaml error handling?  if error, return False
        return True

    def printSizingData(self):
        """print the sizing data we read from the yaml file - NOTE: Remove. Only used for debugging"""
        ## NOTE: Debug only
        if self.sizingData is None:
            print (f'Error: No yaml input: {self.options.argInput}', file=sys.stderr)
            return False
        else:
            ## This would work, but not pretty:  print(self.sizingData)
            print(f'Values read in:')
            for name,val in self.sizingData.items():
                print(f'Value: {name} = {val}')
            print(f'Sizing Values state:')
            print(f'Value: sdi_Colo = {self.sdi_Colo}')
            print(f'Value: sdi_ArchiveUseCase = {self.sdi_ArchiveUseCase}')
            print(f'Value: sdi_StorageCapacity = {self.sdi_StorageCapacity}')
            print(f'Value: sdi_MetaDataCapacity = {self.sdi_MetaDataCapacity}')
            print(f'Value: sdi_DriveCapacity = {self.sdi_DriveCapacity}')
            print(f'Value: sdi_DrivesPerChassis = {self.sdi_DrivesPerChassis}')
            print(f'Value: sdi_PopulatedSlotsPerChassis = {self.sdi_PopulatedSlotsPerChassis}')
            print(f'Value: sdi_NVMeSlotsPerChassis = {self.sdi_NVMeSlotsPerChassis}')
            print(f'Value: sdi_DriveTypeSSD = {self.sdi_DriveTypeSSD}')
            print(f'Value: sdi_MaxFillCapacityPercent = {self.sdi_MaxFillCapacityPercent}')
            print(f'Value: sdi_NVMeRatio = {self.sdi_NVMeRatio}')
            print(f'Value: sdi_ProtectionType = {self.sdi_ProtectionType}')
            print(f'Value: sdi_ECData = {self.sdi_ECData}')
            print(f'Value: sdi_ECParity = {self.sdi_ECParity}')
            print(f'Value: sdc_ECProfile = {self.sdc_ECProfile}')
            print(f'Value: sdc_ComputationalErrors = {self.sdc_ComputationalErrors}')
            return True

    ##
    ## These are all the vTable functions for parsing the passed input
    ##

    def v_Colocation(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_Colo = val
        return True

    def v_ArchiveUseCase(self, val):
        """store sizing data by name from a vTable"""
        ## BUG: The else portion is actually not accurate. It assumes Mixed if not Archive
        lowerval = val.lower()
        self.sdi_ArchiveUseCase = (True if lowerval == 'archive' else False)
        return True

    def v_StorageCapacity(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_StorageCapacity = val
        return True

    def v_MetaDataCapacity(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_MetaDataCapacity = val
        return True

    def v_DriveCapacity(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_DriveCapacity = val
        return True

    def v_DrivesPerChassis(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_DrivesPerChassis = val
        return True

    def v_PopulatedSlotsPerChassis(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_PopulatedSlotsPerChassis = val
        return True

    def v_NVMeSlotsPerChassis(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_NVMeSlotsPerChassis = val
        return True

    def v_DriveTypeSSD(self, val):
        """store sizing data by name from a vTable"""
        lowerval = val.lower()
        self.sdi_DriveTypeSSD = (True if lowerval == 'ssd' else False)
        return True

    def v_MaxFillCapacityPercent(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_MaxFillCapacityPercent = val
        return True

    def v_NVMeRatio(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_NVMeRatio = val
        return True

    def v_ProtectionType(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_ProtectionType = val
        return True

    def v_ECData(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_ECData = val
        return True

    def v_ECParity(self, val):
        """store sizing data by name from a vTable"""
        self.sdi_ECParity = val
        return True


    def validateSizingData(self):
        """check that the sizing data has all the values we expect"""
        if self.sizingData is None:
            print (f'Error: No yaml input: {self.options.argInput}', file=sys.stderr)
            return False
        validated = True;
        ## NOTE: The goal will be to make sure that each value has been input and is verified as appropriate data
        ##       For now, this is only partially implemented.  Still need to check the values.
        # Here's the list of input vars. Validation will require finding each and checking the value passed in
        # colocation: True
        # useCase: 'Mixed'
        # storageCapacity:  2000
        # metaDataCapacity: 0
        # driveCapacity:  16
        # drivesPerChassis: 24
        # populatedSlotsPerChassis: 24
        # nvmeSlotsPerChassis: 6
        # driveType:  'HDD'
        # maxFillCapacity: 80
        # nvmeRatio: 12
        # protectionType:  1
        # ecProfileData: 8
        # ecProfileParity: 3
        #
        # This list is used to search for options - lowercase for flexibility
        inputLowerCaseNames = ['colocation', 'usecase', 'storagecapacity', 'metadatacapacity', 'drivecapacity', 'drivesperchassis', 'populatedslotsperchassis', 'nvmeslotsperchassis', 'drivetype', 'maxfillcapacity', 'nvmeratio', 'protectiontype', 'ecprofiledata', 'ecprofileparity']
        #
        # This dict is used as a vTable, to map options by name to a class method
        inputVTable = {'colocation': self.v_Colocation, 'usecase': self.v_ArchiveUseCase, 'storagecapacity': self.v_StorageCapacity, 'metadatacapacity': self.v_MetaDataCapacity, 'drivecapacity': self.v_DriveCapacity, 'drivesperchassis': self.v_DrivesPerChassis, 'populatedslotsperchassis': self.v_PopulatedSlotsPerChassis, 'nvmeslotsperchassis': self.v_NVMeSlotsPerChassis, 'drivetype': self.v_DriveTypeSSD, 'maxfillcapacity': self.v_MaxFillCapacityPercent, 'nvmeratio': self.v_NVMeRatio, 'protectiontype': self.v_ProtectionType, 'ecprofiledata': self.v_ECData, 'ecprofileparity': self.v_ECParity}
        #
        # Take each passed option, look it up in the tables above and call it's class method, if possible. Else, error
        for key,value in self.sizingData.items():
            if self.options.argVerbose:
                print (f'Validating input: {key}: {value}', file=sys.stdout)
            # Check each option name exists as a key in the Dictionary
            lowerName = key.lower()
            if not lowerName in inputLowerCaseNames:
                # if any of the values are not found, input is invalid
                validated = False
                print (f'Error: Input option not found: {key}: {value}', file=sys.stderr)
            else:
                # this key,value pair is found.  Now, need to store the value
                # NOTE: use a dict to associate the lowercase name with vTable function
                func = inputVTable[lowerName]
                # call the vTable function, passing the value portion of the input
                retval = (func(value) if func else False)
                if not retval:
                    # The value portion wasn't validated, so we need to report that
                    validated = False
                    print(f'Error: Input value not understood: {key}: {value}', file=sys.stderr)
        return True

