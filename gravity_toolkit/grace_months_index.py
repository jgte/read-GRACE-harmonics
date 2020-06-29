#!/usr/bin/env python
u"""
grace_months_index.py
Written by Tyler Sutterley (05/2020)

Creates a file with the start and end days for each dataset
Shows the range of each month for (CSR/GFZ/JPL) (RL04/RL05/RL06)
Shows which months are missing for each dataset as **missing**

INPUTS:
    base_dir: Working data directory for GRACE/GRACE-FO data

OPTIONS:
    DREL: GRACE/GRACE-FO data release (RL04, RL05, RL06)
    MODE: Permissions mode of output index file

OUTPUTS:
    GRACE_months.txt
    Column 1: GRACE Month
    Column 2: Calendar Month and Year
    Column 3: CSR RL06 Dates
    Column 4: GFZ RL06 Dates
    Column 5: JPL RL06 Dates

COMMAND LINE OPTIONS:
    --help: list the command line options
    -D X, --directory=X: Working GRACE/GRACE-FO data directory
    -R X, --release=X: GRACE data releases to run (RL06)
    --mode=X: permissions mode of output GRACE month file

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python (https://numpy.org)

UPDATE HISTORY:
    Updated 05/2020 for public release
"""
from __future__ import print_function

import sys
import os
import getopt
import calendar
import numpy as np

def grace_months_index(base_dir, DREL=['RL06'], MODE=None):

    #-- Output GRACE months file
    grace_months_file = 'GRACE_months.txt'
    fid = open(os.path.join(base_dir,grace_months_file), 'w')

    #-- Initial parameters
    #-- processing centers
    PROC = ['CSR', 'GFZ', 'JPL']
    #-- read from GSM datasets
    DSET = 'GSM'
    #-- maximum month of the datasets
    #-- checks for the maximum month between processing centers
    max_mon = 0
    #-- contain the information for each dataset
    var_info = {}

    #-- Looping through data releases first (all RL04 then all RL05)
    #-- for each considered data release (RL04,RL05)
    for rl in DREL:
        #-- for each processing centers (CSR, GFZ, JPL)
        for pr in PROC:
            #-- Setting the data directory for processing center and release
            grace_dir = os.path.join(base_dir, pr, rl, DSET)
            #-- read GRACE date ascii file
            #-- file created in read_grace.py or grace_dates.py
            grace_date_file = '{0}_{1}_DATES.txt'.format(pr,rl)
            if os.access(os.path.join(grace_dir,grace_date_file), os.F_OK):
                #-- skip the header line
                date_input = np.loadtxt(os.path.join(grace_dir,grace_date_file),
                    skiprows=1)
                #-- number of months
                nmon = np.shape(date_input)[0]

                #-- Setting the dictionary key e.g. 'CSR_RL04'
                var_name = '{0}_{1}'.format(pr,rl)

                #-- Creating a python dictionary for each dataset with parameters:
                #-- month #, start year, start day, end year, end day
                #-- Purpose is to get all of the dates loaded for each dataset
                #-- Adding data to dictionary for data processing and release
                var_info[var_name] = {}
                #-- allocate for output variables
                var_info[var_name]['mon'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['styr'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['stday'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['endyr'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['endday'] = np.zeros((nmon),dtype=np.int)
                #-- place output variables in dictionary
                for i,key in enumerate(['mon','styr','stday','endyr','endday']):
                    #-- first column is date in decimal form (start at 1 not 0)
                    var_info[var_name][key] = date_input[:,i+1].astype(np.int)
                #-- Finding the maximum month measured
                if (var_info[var_name]['mon'].max() > max_mon):
                    #-- if the maximum month in this dataset is greater
                    #-- than the previously read datasets
                    max_mon = np.int(var_info[var_name]['mon'].max())

    #-- sort datasets alphanumerically
    var_name = sorted(var_info.keys())
    txt = ''.join(['{0:^21}'.format(d) for d in var_name])
    #-- printing header to file
    print('{0:^11}  {1}'.format('MONTH',txt),file=fid)

    #-- for each possible month
    #-- GRACE starts at month 004 (April 2002)
    #-- max_mon+1 to include max_mon
    for m in range(4, max_mon+1):
        #-- finding the month name e.g. Apr
        calendar_year = 2002 + (m-1)//12
        calendar_month = (m-1) % 12 + 1
        month_string = calendar.month_abbr[calendar_month]
        #-- create list object for output string
        output_string = []
        #-- for each processing center and data release
        for var in var_name:
            #-- find if the month of data exists
            #-- exists will be greater than 0 if there is a match
            exists = np.count_nonzero(var_info[var]['mon'] == m)
            if (exists != 0):
                #-- if there is a matching month
                #-- indice of matching month
                ind, = np.nonzero(var_info[var]['mon'] == m)
                #-- start date
                st_yr, = var_info[var]['styr'][ind]
                st_day, = var_info[var]['stday'][ind]
                #-- end date
                end_yr, = var_info[var]['endyr'][ind]
                end_day, = var_info[var]['endday'][ind]
                #-- output string is the date range
                #-- string format: 2002_102--2002_120
                output_string.append('{0:4d}_{1:03d}--{2:4d}_{3:03d}'.format(
                    st_yr, st_day, end_yr, end_day))
            else:
                #-- if there is no matching month = missing
                output_string.append(' ** missing **   ')

        #-- create single string with output string components
        #-- formatting the strings to be 20 characters in length
        data_string = ' '.join(['{0:>20}'.format(s) for s in output_string])
        #-- printing data line to file
        args = (m, month_string, calendar_year, data_string)
        print('{0:03d} {1:>3}{2:4d} {3}'.format(*args), file=fid)

    #-- close months file
    fid.close()
    #-- set the permissions level of the output file
    os.chmod(os.path.join(base_dir,grace_months_file), MODE)

#-- PURPOSE: help module to describe the optional input parameters
def usage():
    print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
    print(' -R X, --release=X\tGRACE data releases to run (RL04,RL05)')
    print(' -M X, --mode=X\t\tPermission mode of output GRACE month file\n')

#-- PURPOSE: functional call to grace_months() if running as program
def main():
    #-- Read the system arguments listed after the program
    long_options = ['help','directory=','release=','mode=']
    optlist, arglist = getopt.getopt(sys.argv[1:],'hD:R:M:',long_options)

    #-- command line parameters
    #-- working data directory
    base_dir = os.getcwd()
    #-- data release for output file
    DREL = ['RL06']
    #-- permissions mode of the local directories and files (number in octal)
    MODE = 0o775
    for opt, arg in optlist:
        if opt in ('-h','--help'):
            usage()
            sys.exit()
        elif opt in ("-D","--directory"):
            base_dir = os.path.expanduser(arg)
        elif opt in ("-R","--release"):
            DREL = arg.split(',')
        elif opt in ("-M","--mode"):
            MODE = int(arg, 8)

    #-- run grace months program
    grace_months_index(base_dir, DREL=DREL, MODE=MODE)

#-- run main program
if __name__ == '__main__':
    main()