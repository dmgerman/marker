#!/usr/bin/env python3

# Omar Elazhary (c) 2018

# A variant of Evan's marking script of doom for SML
# (https://github.com/etcwilde/marker)

import argparse
import glob
import logging
from os import listdir
from os import popen
from os.path import abspath, isdir, join
from re import sub
from shutil import copyfile
import subprocess as sp
from sys import exit
from tempfile import mkdtemp

def checkCompilation(filename):
    """
    Checks if the provided script compile via sml.
    """
    command = "sml < %s" % filename
    output = popen(command).read()
    if 'error' in output.lower():
        return (False, output.split('\n'))
    else:
        return (True, output.split('\n'))

def checkTests(filename, testFiles):
    """
    Checks if the provided script passes the tests.
    """
    print(filename)

def listSubSMLFiles(submissionDir):
    subsInit = listdir(submissionDir)
    studentSubs = dict()
    for directoryRaw in subsInit:
        directory = join(submissionDir, directoryRaw)
        searchString = join(directory, '**', '*.sml')
        for filename in glob.iglob(searchString, recursive=True):
            studentSubs[directoryRaw] = filename
    return studentSubs

def listTestSMLFiles(testDir):
    testsInit = listdir(testDir)
    return [join(testDir, x) for x in testsInit]    

def main():
    """
    The script's main function.
    """
    
    # Set up logger
    logger = logging.getLogger('sml-marker')
    logging.basicConfig(level=logging.INFO)
    logger.info('Logger calibrated.')
    
    # Get inputs
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--submissions', type=str, required=True,
                        help='Directory containing student submissions.')
    parser.add_argument('-t', '--tests', type=str, required=True,
                        help='Directory containing assigment tests.')
    parser.add_argument('-o', '--output', type=str, required=True,
                        help='Directory where marking output is stored')

    args = parser.parse_args()
    args.submissions = abspath(args.submissions)
    args.tests = abspath(args.tests)
    args.output = abspath(args.output)

    # Check if the directories exist
    if not isdir(args.submissions):
        logger.fatal('The submissions directory provided does not exist.')
        exit(1)
    if not isdir(args.tests):
        logger.fatal('The tests directory provided does not exist.')
        exit(1)
    if not isdir(args.output):
        logger.fatal('The output directory provided does not exist.')
        
    # Loop over submissions and test them
    submissions = listSubSMLFiles(args.submissions)
    tests = listTestSMLFiles(args.tests)
    for key in submissions.keys():
        tempDir = mkdtemp(dir='/tmp')
        newName = key.replace(', ', '_')
        newName = sub(r'\(.*\)', '', newName)
        logger.info("Processing submission for: %s" % newName)
        newTarget = join(tempDir, 'hw1.sml')
        copyfile(submissions[key], newTarget)
        compResult = checkCompilation(newTarget)
        testResult = checkTests(tempDir, tests)
        break
    
        
        
if __name__ == "__main__":
    main()
