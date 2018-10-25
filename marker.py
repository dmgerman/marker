#!/usr/bin/env python3

# Omar Elazhary (c) 2018

# A variant of Evan's marking script of doom for SML
# (https://github.com/etcwilde/marker)

import argparse
import csv
import glob
import logging
from os import listdir
from os import popen
from os.path import abspath, isdir, join
from re import findall, search, sub
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

def checkTests(dirname, testFiles):
    """
    Checks if the provided script passes the tests.
    """
    tests = []
    testResults = dict()
    # Copy over test file(s)
    for testFile in testFiles:
        testFileName = search('[\w\-]*\.sml', testFile).group(0)
        testFileName = join(dirname, testFileName)
        copyfile(testFile, testFileName)
        tests.append(testFileName)
    # Run tests and save output
    for test in tests:
        command = "cd %s; sml < %s" % (dirname, test)
        output = popen(command).read()
        testName = search('[\w\-]*\.sml', test).group(0)
        if 'error' in output.lower():
            testResults[testName] = (False, output.split('\n'))
        else:
            testResults[testName] = (True, output.split('\n'))
    return testResults

def calculateGrade(compResults, testResults, totalTests):
    # The program does not compile or the tests didn't run
    if not compResults[0] or testResults is None:
        return (0, 0, 0.0)
    # The program compiles and the tests ran so we check them
    grade = 0
    total = totalTests
    for testSuite in testResults.keys():
        testOutput = testResults[testSuite][1]
        for line in testOutput:
            if not line:
                continue
            if 'overall' in line.strip().lower():
                break
            testStatus = search('[0-9]+ out of [0-9]+.*', line.strip())
            if testStatus is not None:
                testNumbers = testStatus.group(0)
                numbers = findall('[0-9]+', testNumbers)
                if line.strip().lower().endswith('failed'):
                    grade += int(numbers[1]) - int(numbers[0])
                else:
                    grade += int(numbers[0])
    return (grade, total, (grade / total))

def writeSubmissionReport(outputDir, submitter, compResults, testResults, totalTests):
    # Calculate grade
    grade = calculateGrade(compResults, testResults, totalTests)
    # Open file
    with open(join(outputDir, submitter + '.md'), 'w') as report:
        submitterReadable = submitter.replace('_', ', ')
        report.write("# %s Submission Report\n" % submitterReadable)
        report.write('\n')
        report.write('### Summary:\n')
        report.write('\n')
        report.write("- Program Compiled: %s\n" % str(compResults[0]))
        report.write("- Tests Passed: %d\n" % grade[0])
        report.write("- Tests Failed: %d\n" % (grade[1] - grade[0]))
        report.write("- Total Tests: %d\n" % grade[1])
        report.write("- Overall Grade: %.2f%%\n" % (grade[2] * 100))
        report.write('\n')
        report.write('### Compilation Output:\n')
        report.write('\n')
        report.write('```\n')
        for line in compResults[1]:
            if line:
                report.write("%s\n" % line)
        report.write('```\n')
        report.write('\n')
        if compResults[0]:
            report.write('### Test Output:\n')
            report.write('\n')
            report.write('```\n')
            for suite in testResults.keys():
                report.write('=====START SUITE=====\n')
                for line in testResults[suite][1]:
                    if line:
                        report.write("%s\n" % line)
                report.write('=====END SUITE=====\n')
            report.write('```\n')
            report.write('\n')

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
    parser.add_argument('-l', '--total', type=int, required=True,
                        help='The total number of tests that will run')

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
        exit(1)

    logger.info("Submission directory is: %s" % args.submissions)
    logger.info("Test directory is: %s" % args.tests)
    logger.info("Output directory is: %s" % args.output)

    # Loop over submissions and test them
    submissions = listSubSMLFiles(args.submissions)
    tests = listTestSMLFiles(args.tests)
    for key in submissions.keys():
        tempDir = mkdtemp(dir='/tmp')
        newName = key.replace(', ', '_')
        newName = sub(r'\(.*\)', '', newName)
        logger.info("Processing submission for: %s" % newName)
        subFile = search('[\w\-]*\.sml', submissions[key]).group(0)
        newTarget = join(tempDir, subFile)
        copyfile(submissions[key], newTarget)
        compResult = checkCompilation(newTarget)
        testResult = None
        if compResult[0]:
            testResult = checkTests(tempDir, tests)
        else:
            logger.info(">> Submission for %s did not compile" % newName)
        # Write individual submission report
        writeSubmissionReport(args.output, newName, compResult, testResult, args.total)
        grades = calculateGrade(compResult, testResult, args.total)
        logger.info(">> %s passed %d tests of %d." % (newName, grades[0], args.total))
        logger.info(">> %s scored %.1f" % (newName, (grades[2] * 100)))
        # Add submitter final grade to grade list
        with open(join(args.output, 'grades.csv'), 'a') as gradesFile:
            writer = csv.writer(gradesFile, delimiter=',', quotechar='"')
            writer.writerow([newName, str(grades[2] * 100)])
        logger.info(">> %s data added to grade list" % newName)
    logger.info("Grade list written to: %s" % join(args.output, 'grades.csv'))


if __name__ == "__main__":
    main()
