#!/usr/bin/python3
import os
import sys
from functools import reduce
from itertools import chain, cycle
import subprocess
from typing import Dict, List, Tuple
from termcolor import colored
import re
import pathlib
import math

# This   # echo "abcdefghijklmnopqrstuvwxyz" | c-smart-search.sh -g "a b c d e f g h i j k l n o p q r s t u v w x y z"
# Link 1 # echo "abcdefghijklmnopqrstuvwxyz" | rpen.py -k a b c d e f g h i j k l n o p q r s t u v w x y z
# Link 2 # echo "abcdefghijklmnopqrstuvwxyz" | h a b c d e f g h i j k l n

# 26 Apr 2021: REFER
#     --> https://stackoverflow.com/questions/17236005/grep-output-with-multiple-colors
#           --> 1. https://github.com/rtulke/rpen
#           --> 2. https://github.com/paoloantinori/hhighlighter
#                 --> Uses 3. http://beyondgrep.com/
#           --> 4. https://github.com/mbornet-hl/hl
#           --> 5. https://github.com/dczhu/cxpgrep
#                 --> Uses the tool "h" from link 2 above

# REFER: https://askubuntu.com/a/558422
# Below used colors: Red, Blue, Yellow, Cyan, Magenta
WORD_COLORS: Tuple = ('1;31;49', '1;34;49', '1;33;49', '1;36;49', '1;35;49')
GROUP_SEPARATOR: str = '1!2@3#4$5%6^7&8*9(0)'


def debug_list(list_var: List, lname: str) -> None:
    print("\n*** *** ***\nDEBUG: " + lname + "\n")
    for i in list_var:
        print(i, end="\n" + GROUP_SEPARATOR + "\n")


def read_file(file_read_command: str,
              input_file_path: str,
              input_group_separator_raw) -> List:
    if file_read_command == 'cat':
        status_code, output = subprocess.getstatusoutput("{} '{}'".format(file_read_command, input_file_path))
    elif file_read_command == 'pdftotext':
        status_code, output = subprocess.getstatusoutput("{} '{}' -".format(file_read_command, input_file_path))
    else:
        status_code, output = subprocess.getstatusoutput(file_read_command.format("'" + input_file_path + "'"))
    output = output.rstrip()

    if status_code != 0:
        # ERROR occurred
        print(output)
        sys.exit(status_code)

    # output_numbered = subprocess.run(['awk', r'''{printf("\033[32m%d:\033[0m %s\n", NR, $0)}''', "-"],
    line_count = output.count('\n')
    max_digit_count = int(math.log10(line_count+1)) + 1
    output_numbered = subprocess.run(['awk', r'''{printf("%0''' + str(max_digit_count) + r'''d: %s\n", NR, $0)}''', "-"],
                                     stdout=subprocess.PIPE,
                                     text=True,
                                     input=output).stdout
    output_numbered = str(output_numbered)

    if input_group_separator_raw is not None:
        if r'\n' in input_group_separator_raw:
            input_group_separator = eval("'" + input_group_separator_raw[:-2].replace(r'\n', r'\n\\d+: ') + input_group_separator_raw[-2:] + "'")
        else:
            input_group_separator = eval("'" + input_group_separator_raw + "'")

        return re.split(
            pattern=input_group_separator,
            string=output_numbered,
        )
    return [output_numbered, ]


def smart_search(file_read_command: str,
                 input_file_path: str,
                 context_lines: int,
                 ignore_case: bool,
                 uniq_words_list: List,
                 input_group_separator_raw: str) -> List:
    global WORD_COLORS, GROUP_SEPARATOR
    # REFER: https://stackoverflow.com/questions/2168065/how-do-i-get-rid-of-line-separator-when-using-grep-with-context-lines/8840902
    command_to_run = ["grep", "-E", "--color=never", "--group-separator", GROUP_SEPARATOR, "-C", str(context_lines)]
    if ignore_case:
        command_to_run.append("-i")
    # debug_list(words_list, "words_list")
    # group1 = subprocess.check_output(command_to_run + ['-n', words_list[0], input_file_path]).decode("utf-8").strip().split(GROUP_SEPARATOR)
    # eval(...) ensures that '\n' and other special characters are properly interpreted
    group1: List = read_file(file_read_command, input_file_path, input_group_separator_raw)
    # debug_list(group1, "group1")
    group2: List = list()

    for word in uniq_words_list:
        if len(group1) == 0:
            break
        for i in group1:
            # REFER: https://stackabuse.com/executing-shell-commands-with-python/
            intermediate_output = subprocess.run(command_to_run + [word], stdout=subprocess.PIPE, text=True, input=i)
            group2.extend(
                str(intermediate_output.stdout).strip('\n').split(GROUP_SEPARATOR)
            )
        group1 = group2
        group2 = list()
    file_segments_matched = list()
    for i in group1:
        i = i.strip('\n')
        if i == '':
            continue
        file_segments_matched.append(i)
    return file_segments_matched


def parse_parameters(parameters: Dict) -> Tuple:
    input_file_path: str = parameters['path']
    file_read_command: str = 'cat'
    if parameters['cmd'] is not None:
        file_read_command = parameters['cmd']
    elif pathlib.Path(input_file_path).suffix == '.pdf':
        file_read_command = 'pdftotext'
    context_lines: int = parameters['C']
    ignore_case: bool = parameters['ignore_case']

    words_list: List = list()
    if parameters['g'] is not None:
        words_list.extend(parameters['g'].split())
    if parameters['w'] is not None:
        words_list.extend(parameters['w'])

    words_list_set = set()
    uniq_words_list = list()
    for i in words_list:
        if i in words_list_set:
            continue
        words_list_set.add(i)
        uniq_words_list.append(i)

    input_group_separator_raw = parameters['input_record_separator']

    return file_read_command, input_file_path, context_lines, ignore_case, uniq_words_list, input_group_separator_raw


def highlight_words(file_segments_matched, words_list: List, ignore_case: bool, no_color: bool, group_separator: str):
    # if ignore_case:
    #     for i in range(len(words_list)):
    #         words_list[i] = words_list[i].lower()

    words_list = list(zip(words_list, cycle(('red', 'blue', 'yellow', 'cyan', 'magenta'))))
    words_list.insert(0, (r'\n\d+: ', 'green'))
    words_list.insert(0, (r'^\d+: ', 'green'))
    print("   words = ", end='')
    for i, (j, k) in enumerate(words_list[2:]):
        if no_color:
            print(j, end='')
        else:
            print(colored(j, k, attrs=['bold']), end='')
        if i < (len(words_list) - 2 - 1):
            print(' , ', end='')
        else:
            print()
    if no_color:
        print("segments = " + str(len(file_segments_matched)))
    else:
        print("segments = " + colored(str(len(file_segments_matched)), color='white', attrs=['bold']))

    for i, segment in enumerate(file_segments_matched):
        # if ignore_case:
        #     segment = segment.lower()
        if no_color:
            print(segment)
        else:
            words_found = list()
            for j, j_color in words_list:
                # REFER: https://www.programiz.com/python-programming/regex
                # REFER: https://stackoverflow.com/questions/19686533/how-to-zip-two-differently-sized-lists
                words_found.extend(
                    list(zip(re.findall(j, segment, flags=re.IGNORECASE if ignore_case else 0), cycle((j_color,)))))
            # REFER: https://stackoverflow.com/questions/57251653/highlight-specific-words-in-a-sentence-in-python
            print(reduce(lambda t, x: t.replace(*x),
                         chain([segment], ((t, colored(t, tcolor, attrs=['bold'])) for t, tcolor in words_found))))
        if i < len(file_segments_matched) - 1:
            if no_color:
                print(group_separator)
            else:
                print(colored(group_separator, 'white', attrs=['bold']))


if __name__ == '__main__':
    # REFER: https://realpython.com/command-line-interfaces-python-argparse/
    import argparse

    # Create the parser
    my_parser = argparse.ArgumentParser(prog='c-smart-search',
                                        description='Smart multi-word search across multiples lines',
                                        epilog='Enjoy the program! :)',
                                        prefix_chars='-',
                                        fromfile_prefix_chars='@',
                                        allow_abbrev=False,
                                        add_help=True)
    my_parser.version = '1.0'

    # DIFFERENCE between Positional and Optional arguments: optional arguments start with - or --, while positional arguments don’t.
    # Add the arguments
    my_parser.add_argument('--version', action='version')
    my_parser.add_argument('-p',
                           '--path',
                           type=str,
                           default='/dev/stdin',
                           help='The path to the text file to search')
    my_parser.add_argument('-i',
                           '--ignore-case',
                           action='store_true',
                           help='Number of lines in the context')
    my_parser.add_argument('-C',
                           metavar='--context',
                           type=int,
                           default=5,
                           help='Number of lines in the context')
    # NOTE: this last option '-g' / '--group' is required because user may not want the
    #       shell to do any text processing on their query
    my_parser.add_argument('-g',
                           metavar='--group',
                           action='store',
                           nargs='?',
                           type=str,
                           help='Any white space separated group of words to search (this gets priority over -w parameter)')
    my_parser.add_argument('-w',
                           metavar='--word',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Word to search')
    my_parser.add_argument('--no-color',
                           action='store_true',
                           help="Do not color the matches found")
    my_parser.add_argument('--group-separator',
                           action='store',
                           type=str,
                           default='--',
                           help='String to separate the groups which matched the input pattern')
    my_parser.add_argument('-R',
                           '--input-record-separator',
                           action='store',
                           type=str,
                           help='String to separate the input based on the record separator. '
                                'This input will be evaluated as python string. So, to use '
                                'newline followed by two hyphen, just write "\\n--". '
                                'Note: input will be evaluated using python syntax. Hence, no need '
                                'to make bash correctly interpret special characters such as "\\n" or "\\t"')
    my_parser.add_argument('--cmd',
                           action='store',
                           type=str,
                           help='Command to use to read the input file and to write the output to stdout. '
                                'Insert {} in the command to insert file name, e.g. "pdftotext {} -"')

    # Execute the parse_args() method
    args: argparse.Namespace = my_parser.parse_args()
    # print('DEBUG: args       = ' + str(args))
    # print('DEBUG: vars(args) = ' + str(vars(args)))
    # print('DEBUG: vars(args) = \n\t\t\t' +
    #       str('\n\t\t\t'.join(['{:30} : {}'.format(i, j) for i, j in vars(args).items()])))

    # REFER: https://stackoverflow.com/questions/6722936/python-argparse-make-at-least-one-argument-required
    if not (args.w or args.g):
        my_parser.error('No action requested, add -process or -upload')

    input_file_path = args.path
    if not (os.path.exists(input_file_path)) or os.path.isdir(input_file_path):
        print('The file path specified does not exist')
        sys.exit()

    # search_parameters ---> (file_read_command, input_file_path, context_lines, ignore_case, uniq_words_list, input_group_separator_raw)
    search_parameters: Tuple = parse_parameters(parameters=vars(args))
    # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 5, 'w': ['an[a-z]', 'what', 'is', 'o[a-z]'], 'g': None})
    # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 1, 'w': None, 'g': 'an'})

    # print('DEBUG: words_list = ' + str(search_parameters[3]))
    file_segments_matched: List = smart_search(*search_parameters)
    highlight_words(file_segments_matched=file_segments_matched,
                    words_list=search_parameters[4],
                    ignore_case=search_parameters[3],
                    no_color=args.no_color,
                    group_separator=eval("'" + args.group_separator + "'"))

    # Both the EXAMPLE's will give the same result
    # python c-smart-search.py -C 5 -i -g 'an[a-z] what is o[a-z] vms' "./Q and A.md"
    # python c-smart-search.py -C 5 -i -w 'an[a-z]' -w 'what' -w 'is' -w 'o[a-z]' -w 'vms' "./Q and A.md"
