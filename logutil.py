#!/usr/bin/python3
import argparse
import os
import re
import sys
from typing import Callable

HELP = """Expected arguments:
* directory (optional)
* search string (mandatory)"""


def die(message: str):
    print(message, file=sys.stderr)
    sys.exit(1)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Arguments:
    directories: str
    search_expression: str
    log_file_name_suffix = '.log'
    show_exceptions = False
    show_file_name = True
    # When true program exits on first line that don't have match key.
    # When false then lines without match key are displayed at the bottom.
    break_on_date_missing = False


date_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}')


def get_date(line: str) -> str:
    search = date_pattern.match(line)
    if search:
        return search.group(0)
    return ''


class MatchKeyMissingError(ValueError):
    def __init__(self, message):
        self.message = message


class LogFile:
    file_name: str
    simple_file_name: str
    current_line: str
    current_match: str
    next_line: str
    line_number: int
    eof: bool
    extract_match_key_func: Callable[[str], str]
    search_expression: str
    full_exceptions: bool
    break_on_match_key_missing: bool
    missing_date_lines: [str]

    def __init__(self,
                 file_name: str,
                 extract_match_key_func: Callable[[str], str],
                 search_expression: str,
                 full_exceptions: bool,
                 break_on_match_key_missing: bool):
        self.file_name = file_name
        self.simple_file_name = re.sub(r'^.*/', '', file_name)
        self.extract_match_key_func = extract_match_key_func
        self.search_expression = search_expression
        self.full_exceptions = full_exceptions
        self.break_on_match_key_missing = break_on_match_key_missing
        self.missing_date_lines = []
        self.line_number = 0
        self.eof = False

        self.file = open(file_name, "r")
        self.read_next_line_from_file()
        self.read_line()

    def read_next_line_from_file(self):
        self.next_line = self.file.readline()
        self.line_number += 1

    def read_line(self):
        while True:
            self.current_line = self.next_line
            current_line_number = self.line_number

            if not self.current_line:
                self.eof = True
                return

            self.read_next_line_from_file()

            if self.current_line.startswith("20"):
                while self.next_line and not self.next_line.startswith("20"):
                    if self.full_exceptions:
                        self.current_line += self.next_line
                    self.read_next_line_from_file()

            self.current_line = self.current_line.strip()

            if len(self.current_line) > 0 and self.search_expression in self.current_line:
                replacement = bcolors.BOLD + bcolors.WARNING + self.search_expression + bcolors.ENDC
                self.current_line = self.current_line.replace(self.search_expression, replacement, 9999)
                self.current_match = self.extract_match_key_func(self.current_line)
                if len(self.current_match) > 0:
                    return
                elif self.break_on_match_key_missing:
                    raise MatchKeyMissingError(f"Cannot extract date: file {self.file_name}, " +
                                               f"line number {current_line_number}:\n{self.current_line}")
                else:
                    self.missing_date_lines.append(str(current_line_number) + ": " + self.current_line)

    def close(self):
        self.file.close()


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description="Search multiple log files, sorts results by date.")
    parser.add_argument("SearchExpression", metavar="expression", type=str, help="the search expression")
    parser.add_argument("Directories", metavar="directories", type=str, nargs='*', help="the list of log directories")
    parser.add_argument("-e", action="store_true", help="show full exceptions")
    parser.add_argument("-i", action="store_true", help="ignore missing date")
    parser.add_argument("-f", action="store_true", help="show file names")
    args = parser.parse_args()

    result = Arguments()
    result.search_expression = args.SearchExpression
    result.directories = args.Directories
    if len(result.directories) == 0:
        result.directories = ['.']
    result.show_exceptions = args.e
    result.break_on_date_missing = not args.i
    result.show_file_name = args.f
    return result


def get_log_file_names(directories: [str], log_file_name_suffix: str) -> [str]:
    result = []
    for directory in directories:
        if not os.path.isdir(directory):
            die(f'{directory} is not a directory')
        result += [os.path.join(directory, file) for file in os.listdir(directory)]

    def is_log_file(file_name: str):
        return os.path.isfile(file_name) and file_name.endswith(log_file_name_suffix)

    return list(filter(is_log_file, result))


def grep_for_logs(arguments: Arguments):
    file_names = get_log_file_names(arguments.directories, arguments.log_file_name_suffix)
    file_names.sort()

    if len(file_names) > 20:
        file_names = "\n ".join(file_names)
        die(f'Too many files ({len(file_names)}:\n  {file_names}')

    log_files = []
    for name in file_names:
        log_file = LogFile(file_name=name,
                           extract_match_key_func=get_date,
                           search_expression=arguments.search_expression,
                           full_exceptions=arguments.show_exceptions,
                           break_on_match_key_missing=arguments.break_on_date_missing)
        log_files.append(log_file)

    try:
        open_files = list(filter(lambda file: not file.eof, log_files))

        # check id all not closed
        while True:
            # this can be optimized by removing eof files from log_files
            if len(open_files) == 0:
                break

            min_open = min(open_files, key=lambda x: x.current_match)

            line = min_open.current_line

            if arguments.show_file_name:
                line = bcolors.OKBLUE + min_open.simple_file_name + bcolors.ENDC + ":" + line

            print(line)

            min_open.read_line()
            if min_open.eof:
                open_files.remove(min_open)

        print_missing_date_lines(log_files)
    except MatchKeyMissingError as error:
        die("ERROR - EXITING: " + error.message)
    finally:
        [log_file.close() for log_file in log_files]


def print_missing_date_lines(log_files):
    missing_keys_header_printed = False
    for log_file in log_files:
        if len(log_file.missing_date_lines) > 0:
            if not missing_keys_header_printed:
                print("--------- ERRORS: missing match key -----------------------------------------------")
                missing_keys_header_printed = True
            print("File:", log_file.file_name)
            for line in log_file.missing_date_lines:
                print("  Line ", line)


# Program starts here
parsed_args = parse_arguments()

grep_for_logs(parsed_args)
