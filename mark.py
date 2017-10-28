#!/bin/env python3
# Evan Wilde (c) 2017

# My big insane marking script of doom 😈

import argparse
import os
import sys
import csv
import re
import shutil
import subprocess
from subprocess import call


username_pattern = r".*\((.*)\)$"
username_expr = re.compile(username_pattern)

test_pattern = r"(100|[1-9][0-9]|[0-9])% tests passed, ([0-9]+) tests failed out of ([0-9]+)"
test_expr = re.compile(test_pattern)


## Helper Functions

# Deletes files in folder, it ignores filenames in ignore list
def removeFiles(folder, ignore=[], skipdirs=True):
    "Deletes all files that are in folder"
    for f in os.listdir(folder):
        if f in ignore:
            continue
        try:
            fpath = os.path.join(folder, f)
            if os.path.isfile(fpath):
                os.remove(fpath)
            elif os.path.isdir(fpath) and not skipdirs:
                shutil.rmtree(fpath)
        except Exception as e:
            print(f"Threw an exception {e}")

# from, to (copies all files in from, to the to dir)
def copyContents(f, t):
    "Copy all files in f into t dir"
    [shutil.copy(os.path.join(f, p), t)
            if os.path.isfile(os.path.join(f, p))
            else shutil.copytree(os.path.join(f, p), os.path.join(t, p))
            for p in os.listdir(f)]

## Viewer Modes
def editFile(fname):
    if os.environ.get('EDITOR'):
        subprocess.run([os.environ.get("EDITOR"), fname])
    else: # Rudimentary backup editor
        lines = []
        while True:
            try:
                line = input(">>>")
            except EOFError:
                break
            lines.append(line)
        contents = '\n'.join(lines)
        with open(fname, 'w') as FILE:
            FILE.write(contents)
        print("\r", end='')

def appendToFile(fname, content):
    with open(fname, 'a+') as FILE:
        FILE.write(content)

# Show stuff
def viewData(content):
    PAGER = os.environ.get('PAGER')
    if PAGER and len(content.split('\n')) > 20:
        if PAGER == 'less':
            subprocess.run([os.environ.get("PAGER"), '-N'], input=content.encode('utf-8'))
        else:
            subprocess.run([os.environ.get("PAGER")], input=content.encode('utf-8'))
    else:
        os.system("clear")
        print(content)

# Read a file and show it
def viewFile(fname):
    if os.path.isfile(fname):
        with open(fname, 'r') as FILE:
                viewData(FILE.read())

# Get files in a directory
def getFiles(dirc):
    return [x for x in os.listdir(dirc) if x is not os.path.isdir(x)]

# Prompt user to select an item
def selectItems(itms):
    prmt = '\t' + '\n\t'.join([f"({num+1}): {nm}"
        for num, nm in enumerate(itms)]) + '\n [1] >>: '
    while True:
        i = input(prmt)
        if i == '':
            return (0, itms[0])
        try:
            select = int(i)
        except ValueError:
            continue
        if select <= len(itms) and select > 0:
            return (select-1, itms[select-1])

## Main Functions
def loadTmpDir(submissiondir, assndir, tmpdir, outputdir):
    """Load user submission to staging area

    Loads the testing files into the tmpdir
    Will create build folder and cd into that for compiling and marking

    Calls the compile and marking functions.

    If the program does not compile, the submission receives a zero and is not
    passed forward to marking.

    :rootdir: The root directory where the assignments are (directory with
    student names)
    :tmpdir: Where compilation and marking are occurring
    :assndir: location where original assignment is kept
    """

    # Deals with the joys of connex BS
    # Copy and open grade file
    in_gradefname = os.path.join(submissiondir, 'grades.csv')
    out_gradefname = os.path.join(outputdir, 'grades.csv')
    if not os.path.exists(in_gradefname):
        print("grade.csv doesn't exist", "Re-download submissions from Connex with grade.csv included", sep="\n", file=sys.stderr)
        exit(1)
    with open(in_gradefname, 'r') as gradeFile:
        gradeReader = csv.reader(gradeFile, delimiter=',')
        l = [row for row in gradeReader]
        header = l[:3]
        order = [stud[1] for stud in l[3:]]
        details = {stud[1]: stud for stud in l[3:]}
    submissions = {username_expr.search(p).groups()[0]: p for p in os.listdir(submissiondir) if username_expr.search(p)}
    assert len(details) == len(submissions) # If these don't match, panic
    cwd = os.getcwd() # Store this so we can go back to it later
    # And here we go with actually driving this stupid boat
    for idx, f in enumerate(details):
        submission_path = os.path.join(submissiondir, submissions[f], "Submission attachment(s)")
        output_path = os.path.join(outputdir, submissions[f])
        # If it has already been marked, show the marks and copy the comments file
        if details[f][-1]:
            if os.path.isfile(os.path.join(submissiondir, submissions[f], 'comments.txt')):
                shutil.copy(os.path.join(submissiondir, submissions[f], 'comments.txt'), tmpdir)
            resp = input(f"{f}[{details[f][-1]}] already marked: Remark? [y/N]:")
            if resp.lower() != 'y':
                # Copy comment file
                if not os.path.isfile(os.path.abspath("./comments.txt")):
                    with open(os.path.abspath("./comments.txt"), 'w'):
                        pass # Just create it and leave
                if not os.path.isdir(output_path):
                    os.mkdir(output_path)
                shutil.copy(os.path.abspath("./comments.txt"),
                        os.path.join(output_path, "comments.txt"))
                continue

        copyContents(submission_path, tmpdir)
        copyContents(assndir, tmpdir)  # Will overwrite anything already there
        if not os.path.isdir(os.path.join(tmpdir, 'build')):
            os.mkdir(os.path.join(tmpdir, 'build'))
        os.chdir(os.path.join(tmpdir, 'build'))
        compiled, compile_msg = cpp_compile() # compile submission

        if compiled:
            score, output, correct, total = mark()
        else:
            score = 0
            output = "Failed to compile"
            correct = 0
            total = 0

        # Okay, back to the workdir for comments and shipping the mark
        os.chdir(tmpdir)
        options = ["Keep",
                "Comment",
                "Replace Grade",
                "Show Compiler Output",
                "Show Test Output",
                "Show Comment",
                "Append compiler message",
                "Append Test Output",
                "View Submission"]

        while True:
            print(f"""Marking {submissions[f]}:
Student {idx+1} / {len(details)}
Mark: {score} ({correct} / {total})""")
            idx, cmd = selectItems(options)
            if idx == 0:
                break
            elif idx == 1: # Comment on file
                editFile(os.path.abspath("./comments.txt"))
                continue
            elif idx == 2: # Change grade
                score = round(float(input("New Grade: ")), 2)
                continue
            elif idx == 3:
                viewData(compile_msg)
            elif idx == 4:
                viewData(output)
            elif idx == 5:
                viewFile(os.path.abspath("./comments.txt"))
            elif idx == 6:
                appendToFile(os.path.abspath("./comments.txt"),
                        '\n'.join(["\n<pre>","=== [Compiler Output] =========",
                            compile_msg, "</pre>"]))
            elif idx == 7:
                appendToFile(os.path.abspath("./comments.txt"),
                        '\n'.join(["\n<pre>", "=== [Test Output] =============",
                            output, "</pre>"]) )
            elif idx == 8:
                submittedFiles = getFiles(submission_path)
                if len(submittedFiles) > 1:
                    _, fname = selectItems(submittedFiles)
                else:
                    fname = submittedFiles[0]
                viewFile(os.path.abspath("./" + fname))
            else:
                print(idx, cmd)
        # Once everything is hunky dory, put away their mark and move on
        details[f][-1] = score

        if not os.path.isfile(os.path.abspath("./comments.txt")):
            with open(os.path.abspath("./comments.txt"), 'w'):
                pass # Just create it and leave
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
        shutil.copy(os.path.abspath("./comments.txt"),
                os.path.join(output_path, "comments.txt"))
        removeFiles(os.path.join(tmpdir, "build"), skipdirs=False)
        shutil.rmtree(os.path.join(tmpdir, "tests"))
        removeFiles(tmpdir, skipdirs=False)
    os.chdir(cwd)
    # Write grades to grade file
    with open(os.path.join(outputdir, "grades.csv"), "w") as outputgrades:
        csv_writer = csv.writer(outputgrades, dialect='unix')
        [csv_writer.writerow(el) for el in header]
        [csv_writer.writerow(details[stud]) for stud in order]

    return details

# Compile submission
def cpp_compile(threads=2):
    """Compile the user submission
    CMakeLists.txt should be in the cwd

    :returns: True/False depending on if the program compiles
    """
    cmake_ret = subprocess.run(["cmake", "../"], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = cmake_ret.stdout
    errors = cmake_ret.stderr

    output = ""
    errors = ""

    make_ret = subprocess.run(["make", f"-j{threads}"], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = make_ret.stdout
    errors = make_ret.stderr
    return (make_ret.returncode == 0, errors if make_ret != 0 else None)

# Mark submission loaded in tmp dir
def mark():
    """Mark student submissions using the test file

    Runs "make test" in cwd

    :returns: score
    """
    test_ret = subprocess.run(["make", "test"], encoding='utf-8',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    output = test_ret.stdout
    errors = test_ret.stderr

    lines = output.split('\n')

    # find the line with the info we are looking for

    i = 0
    for idx, l in enumerate(lines):
        if "% tests passed," in l:
            i = idx
    m = test_expr.search(lines[i])
    if m:
        perc, wrong, total = m.groups()
        perc = float(perc) / 100 # percent
        wrong = int(wrong)
        total = int(total)
        right = total - wrong
    else:
        print('\n'.join(lines))
        right = int(input("Failed to parse score, input correct number manually: "))
        total = int(input("Total tests: "))
    comp = right / total
    output = '\n'.join([lines[0]]+lines[2:])
    return (100 * comp, output, right, total)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '--submissions', type=str, required=True,
            help="Directory containing student submissions")
    ap.add_argument('-t', '--template', type=str, required=True,
            help="Directory containing the assignment materials and tests")
    ap.add_argument('-w', '--working', type=str, default='./tmp',
            help="Temporary working directory")
    ap.add_argument('-o', '--output', type=str, default='./output',
            help="Directory where marked output is stored.")
    # TODO: Add zip functionality


    args=ap.parse_args()
    args.submissions = os.path.abspath(args.submissions)
    args.template = os.path.abspath(args.template)
    args.working = os.path.abspath(args.working)
    args.output = os.path.abspath(args.output)

    # Check if necessary directories exist
    if not os.path.isdir(args.submissions):
        print("Submission directory does not exist", file=sys.stderr)
        exit(1)

    if not os.path.isdir(args.template):
        print("Assignment template directory does not exist", file=sys.stderr)
        exit(1)

    if os.path.isdir(args.working):
        shutil.rmtree(args.working)
    os.mkdir(args.working)

    if os.path.isdir(args.output):
        shutil.rmtree(args.output)
    os.mkdir(args.output)

    # Run through each submission and try it
    loadTmpDir(args.submissions, args.template, args.working, args.output)
    shutil.rmtree(args.working)


if __name__ == "__main__":
    main()
