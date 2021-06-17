#!/usr/bin/python3
import gc
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
#           --> 1. https://github.com/mbornet-hl/hl
#           --> 2. https://github.com/paoloantinori/hhighlighter
#                 --> Uses 3. http://beyondgrep.com/
#                             https://github.com/beyondgrep/ack3
#           --> 4. https://github.com/rtulke/rpen
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
              input_group_separator_raw: str,
              add_line_number: bool) -> List:
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

    if add_line_number:
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
    else:
        output_numbered = output
        if input_group_separator_raw is not None:
            return re.split(
                pattern=eval("'" + input_group_separator_raw + "'"),
                string=output_numbered
            )

    return [output_numbered, ]


def smart_search(file_read_command: str,
                 input_file_path: str,
                 context_lines: int,
                 ignore_case: bool,
                 uniq_words_list: List,
                 input_group_separator_raw: str,
                 add_line_number: bool) -> List:
    global WORD_COLORS, GROUP_SEPARATOR
    # REFER: https://stackoverflow.com/questions/2168065/how-do-i-get-rid-of-line-separator-when-using-grep-with-context-lines/8840902
    command_to_run = ["grep", "-E", "--color=never", "--group-separator", GROUP_SEPARATOR, "-C", str(context_lines)]
    if ignore_case:
        command_to_run.append("-i")
    # debug_list(words_list, "words_list")
    # group1 = subprocess.check_output(command_to_run + ['-n', words_list[0], input_file_path]).decode("utf-8").strip().split(GROUP_SEPARATOR)
    # eval(...) ensures that '\n' and other special characters are properly interpreted
    group1: List = read_file(file_read_command, input_file_path, input_group_separator_raw, add_line_number)
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
        gc.collect()
        # debug_list(group1, "group1")
    file_segments_matched = list()
    for i in group1:
        i = i.strip('\n')
        if i == '':
            continue
        file_segments_matched.append(i)
    gc.collect()
    return file_segments_matched


def parse_parameters(parameters: Dict, input_file_path: str) -> Tuple:
    file_read_command: str = 'cat'
    if parameters['cmd'] is not None:
        file_read_command = parameters['cmd']
    elif pathlib.Path(input_file_path).suffix == '.pdf':
        file_read_command = 'pdftotext'
    context_lines: int = parameters['C']
    ignore_case: bool = parameters['ignore_case']

    words_list: List = list()
    if parameters['g'] is not None:
        for i in parameters['g']:
            words_list.extend(i.split())
    if parameters['w'] is not None:
        words_list.extend(parameters['w'])
    if parameters['q'] is not None:
        for i in parameters['q']:
            words_list.append('({})?'.format(i))

    words_list_set = set()
    uniq_words_list = list()
    for i in words_list:
        if i in words_list_set:
            continue
        words_list_set.add(i)
        uniq_words_list.append(i)

    input_group_separator_raw = parameters['input_record_separator']
    add_line_number = parameters['line_number']
    return file_read_command, input_file_path, context_lines, ignore_case, \
           uniq_words_list, input_group_separator_raw, add_line_number


def highlight_words(file_segments_matched, words_list: List, ignore_case: bool, no_color: bool, group_separator: str):
    # if ignore_case:
    #     for i in range(len(words_list)):
    #         words_list[i] = words_list[i].lower()

    words_list = list(zip(
        words_list, 
        cycle((
            ('red', ('bold',) ),
            ('blue', ('bold',) ),
            ('yellow', ('bold',) ),
            ('cyan', ('bold',) ),
            ('magenta', ('bold',) ),

            # ('red', ('bold', 'dark',) ),
            # ('blue', ('bold', 'dark',) ),
            # ('yellow', ('bold', 'dark',) ),
            # ('cyan', ('bold', 'dark',) ),
            # ('magenta', ('bold', 'dark',) ),

            ('red', ('bold', 'underline',) ),
            ('blue', ('bold', 'underline',) ),
            ('yellow', ('bold', 'underline',) ),
            ('cyan', ('bold', 'underline',) ),
            ('magenta', ('bold', 'underline',) ),

            ('red', ('bold', 'reverse',) ),
            ('blue', ('bold', 'reverse',) ),
            ('yellow', ('bold', 'reverse',) ),
            ('cyan', ('bold', 'reverse',) ),
            ('magenta', ('bold', 'reverse',) ),
        ))
    ))
    # words_list.insert(0, (r'\n\d+: ', ('green', None) ))
    # words_list.insert(0, (r'^\d+: ', ('green', None) ))
    words_list.insert(0, (r'\n[0-9]+: ', ('green', None) ))
    words_list.insert(0, (r'^[0-9]+: ', ('green', None) ))
    print("   words = ", end='')
    for i, (j, (k_color, k_attr)) in enumerate(words_list[2:]):
        if no_color:
            print(j, end='')
        else:
            print(colored(j, k_color, attrs=k_attr), end='')
        if i < (len(words_list) - 2 - 1):
            print(' , ', end='')
        else:
            print()
    if no_color:
        print("segments = " + str(len(file_segments_matched)))
    else:
        print("segments = " + colored(str(len(file_segments_matched)), color='white', attrs=['bold']))

    command_to_run = ["grep", "-E", "--color=never", "-o"]
    if ignore_case:
        command_to_run.append("-i")
    def get_match_list(temp_regex, temp_str):
        a=str(subprocess.run(command_to_run + [temp_regex], stdout=subprocess.PIPE, text=True, input=temp_str).stdout).strip('\n').split('\n')
        # print("----------")
        # print(temp_regex, a)
        # print("***")
        # print(temp_str)
        # print("----------")
        if len(a) == 1 and a[0].strip() =='':
            return list()
        return a

    for i, segment in enumerate(file_segments_matched):
        # if ignore_case:
        #     segment = segment.lower()
        if no_color:
            print(segment)
        else:
            words_found = list()
            for j, j_color_attr in words_list:                
                # REFER: https://www.programiz.com/python-programming/regex
                # REFER: https://stackoverflow.com/questions/19686533/how-to-zip-two-differently-sized-lists
                
                # NOTE/WARNING: re.findall is not working as expected with input="ether 00:50:56:c0:00:08  txqueuelen 1000  (Ethernet)" and regex='([0-9a-f]{2}:){5}[0-9a-f]{2}'
                # words_found.extend(list(
                #     zip(re.findall(j, segment, flags=re.IGNORECASE if ignore_case else 0), cycle((j_color_attr,)))
                # ))

                words_found.extend(list(
                    zip(get_match_list(j, segment), cycle((j_color_attr,)))
                ))

            # REFER: https://stackoverflow.com/questions/57251653/highlight-specific-words-in-a-sentence-in-python
            print(
                reduce(
                    lambda t, x: t.replace(*x),
                    chain([segment], ((t, colored(t, t_color, attrs=t_attr)) for t, (t_color, t_attr) in words_found))
                )
            )
            # for x in [(t, colored(t, t_color, attrs=t_attr)) for t, (t_color, t_attr) in words_found]:
            #     segment = segment.replace(*x)
            #     gc.collect()
        if i < len(file_segments_matched) - 1:
            if no_color:
                print(group_separator)
            else:
                print(colored(group_separator, 'white', attrs=['bold']))
        gc.collect()


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
                           action='append',
                           nargs='?',
                           type=str,
                           help='The path to the text file to search')
    my_parser.add_argument('-P',
                           '--Paths',
                           action='store',
                           nargs='+',
                           type=str,
                           help='The list of paths to the text files to search')
    my_parser.add_argument('-i',
                           '--ignore-case',
                           action='store_true',
                           help='Ignore case while searching')
    my_parser.add_argument('-C',
                           metavar='--context',
                           type=int,
                           default=5,
                           help='Number of lines in the context')
    # NOTE: this last option '-g' / '--group' is required because user may not want the
    #       shell to do any text processing on their query
    my_parser.add_argument('-g',
                           metavar='--group',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Any white space separated group of words to search (this gets priority over -w parameter)')
    my_parser.add_argument('-w',
                           metavar='--word',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Word to search')
    my_parser.add_argument('-q',
                           metavar='--quiet',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Optional words to search')
    my_parser.add_argument('-Q',
                           action='store_true',
                           help='Do not print anything for files in which no results found')
    my_parser.add_argument('--no-color',
                           action='store_true',
                           help="Do not color the matches found")
    my_parser.add_argument('-n',
                           '--line-number',
                           action='store_true',
                           help='Print line number (NOTE: printing line numbers may cause problem with REGEX matching)')
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
    if not (args.g or args.w or args.q):
        my_parser.error('No action requested, add -g or -w or -q')

    if args.path is None:
        if args.Paths is None:
            args.path=['/dev/stdin']
        else:
            args.path = args.Paths
    else:
        if args.Paths is not None:
            (args.path).extend(args.Paths)

    for input_file_path in args.path:
        if not (os.path.exists(input_file_path)) or os.path.isdir(input_file_path):
            # print('The file path specified does not exist')
            print('CANNOT open \'{}\' for reading: No such file or directory'.format(colored(input_file_path, 'white', attrs=['bold', 'underline'])))
            continue

        # search_parameters ---> (file_read_command, input_file_path, context_lines, ignore_case, uniq_words_list, input_group_separator_raw)
        search_parameters: Tuple = parse_parameters(parameters=vars(args), input_file_path=input_file_path)
        # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 5, 'w': ['an[a-z]', 'what', 'is', 'o[a-z]'], 'g': None})
        # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 1, 'w': None, 'g': 'an'})

        # print('DEBUG: words_list = ' + str(search_parameters[3]))
        file_segments_matched: List = smart_search(*search_parameters)
        if (args.Q == False) or  len(file_segments_matched) > 0:
            if len(args.path) > 1:
                print('==> {} <=='.format(colored(input_file_path, 'white', attrs=['bold', 'underline'])))
            highlight_words(file_segments_matched=file_segments_matched,
                            words_list=search_parameters[4],
                            ignore_case=search_parameters[3],
                            no_color=args.no_color,
                            group_separator=eval("'" + args.group_separator + "'"))
            if len(args.path) > 1:
                print()

        gc.collect()

    # Both the EXAMPLE's will give the same result
    # python c-smart-search.py -C 5 -i -g 'an[a-z] what is o[a-z] vms' "./Q and A.md"
    # python c-smart-search.py -C 5 -i -w 'an[a-z]' -w 'what' -w 'is' -w 'o[a-z]' -w 'vms' "./Q and A.md"

    # my     ifconfig | c-fms -C 1000 -q '([a-z]+[0-9]*)+: ' -q '([0-9a-f]{2}:){5}[0-9a-f]{2}' -q '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -q '^(eth|(vir)?br|vnet)[0-9.:]*\>' -q '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -q '(errors|dropped|overruns):[^0][0-9]*'
    # sof    ifconfig | c-fms -C 1000 -q '^(eth|(vir)?br|vnet)[0-9.]*:[0-9]+\>' -q '^(eth|(vir)?br|vnet)[0-9.]*\.[0-9]+\>' -q '([0-9a-f]{2}:){5}[0-9a-f]{2}' -q '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -q '^(eth|(vir)?br|vnet)[0-9.:]*\>' -q '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -q ' (errors|dropped|overruns):[^0][0-9]*'
    # github ifconfig | c-fms -C 1000 -q 'inet addr:([0-9]{1,3}(\.[0-9]{1,3}){3})' -q '^((eth|(vir)?br|vnet)[0-9.]*:[0-9]+)\>' -q '^((eth|(vir)?br|vnet)[0-9.]*\.[0-9]+)\>' -q '(([0-9a-f]{2}:){5}[0-9a-f]{2})' -q '(\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>)' -q '(^(eth|(vir)?br|vnet)[0-9.:]*)\>' -q '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -q ' ((errors|dropped|overruns):[^0][0-9]*)'

    # ip a | c-fms -C 1000 -q '\<((([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]))\>'
    # ps -e | c-fms -C 100000 -q '((0[1-9]|[1-9][0-9])(:[0-9]{2}){2} .*)' -q '(00:00:[1-9][0-9] .*)' -q '(00:(0[1-9]|[1-9][0-9]):[0-9]{2} .*)'
