#!/usr/bin/env python
#!/usr/bin/python3
import gc
import os
import sys
from itertools import cycle
import subprocess
from typing import Dict, List, Tuple
import neotermcolor
import re
import pathlib
import math
import logging

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

# REFER for Coloring Text In Terminal: https://askubuntu.com/a/558422

# Here "+" is used to create the "GROUP_SEPARATOR" to avoid wrong splitting when this program is used on itself
GROUP_SEPARATOR: str = 'fms_1!2@3#4$5%' + '6^7&8*9(0)_smf'
COLOR_OUTPUT_TEXT: bool = True
EXIT_CODE: int = 1
logger = None


def debug_list(list_var: List, lname: str) -> None:
    print("\n*** *** ***\nDEBUG: " + lname + "\n")
    for i in list_var:
        print(i, end="\n" + GROUP_SEPARATOR + "\n")


def my_colored(text, color=None, on_color=None, attrs=None):
    global COLOR_OUTPUT_TEXT
    if COLOR_OUTPUT_TEXT:
        return neotermcolor.colored(text, color, on_color, attrs)
    return text


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
        print("{}: Unable to read file \'{}\'".format(my_colored('Error', 'red', attrs=['bold']), input_file_path), file=sys.stderr)
        print("{}: status_code = {}".format(my_colored('Error', 'red', attrs=['bold']), str(status_code)), file=sys.stderr)
        print("{}: Output:".format(my_colored('Error', 'red', attrs=['bold'])), file=sys.stderr)
        print(output, file=sys.stderr)
        print("\nExiting...", file=sys.stderr)
        sys.exit(status_code)

    if input_group_separator_raw is not None:
        # This "replace" is required because single quotes are used in "eval" statements later
        input_group_separator_raw = input_group_separator_raw.replace("'", r"\'")

    if add_line_number:
        # output_numbered = subprocess.run(['awk', r'''{printf("\033[32m%d:\033[0m %s\n", NR, $0)}''', "-"],
        # TODO: Windows line separator may not work correctly
        line_count = output.count('\n') + 1  # This line count is equal to what Vim shows
        max_digit_count = int(math.log10(line_count)) + 1
        global GROUP_SEPARATOR
        # "-F" parameter is used to avoid un-necessary work by awk
        output_numbered = subprocess.run(['awk', '-F', GROUP_SEPARATOR, r'{printf("%0' + str(max_digit_count) + r'd: %s\n", NR, $0)}', '-'],
                                        stdout=subprocess.PIPE,
                                        text=True,
                                        input=output).stdout
        output_numbered = str(output_numbered)
        if input_group_separator_raw is not None:
            if r'\n' in input_group_separator_raw:
                # At present, -n and -I work together properly only if -I has only
                #     1. newline "\n" characters or
                #     2. a simple string without any newline character (regex without "^" and "$" are fine)

                # TODO: This needs to be fixed. It can not handle all splits when "-n" parameter is there
                # TODO: Check if -2 is required or -1 is required
                # NOTE: Previously it was -2
                # Last new line need not be replaced
                input_group_separator = eval("'" + input_group_separator_raw[:-1].replace(r'\n', r'\n\\d+: ') + input_group_separator_raw[-1:] + "'")
                # input_group_separator = eval("'" + input_group_separator_raw.replace(r'\n', r'\n\\d+: ') + "'")
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
    global GROUP_SEPARATOR
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
    if parameters['W'] is not None:
        for i in parameters['W']:
            words_list.append('({})?'.format(i))

    add_line_number = parameters['line_number']
    words_list_set = set()
    uniq_words_list = list()
    for i in words_list:
        if i in words_list_set:
            continue
        words_list_set.add(i)
        if add_line_number and i[0] == '^':
            uniq_words_list.append("^([0-9]+: )?(" + i[1:] + ")")  # replace "^" with "^([0-9]+: )?" to handle leading line number
        else:
            uniq_words_list.append(i)

    input_group_separator_raw = parameters['input_record_separator']
    return file_read_command, input_file_path, context_lines, ignore_case, \
           uniq_words_list, input_group_separator_raw, add_line_number


def highlight_words(file_segments_matched, words_list: List, ignore_case: bool, output_segment_separator: str, verbose: bool):
    # if ignore_case:
    #     for i in range(len(words_list)):
    #         words_list[i] = words_list[i].lower()
    global COLOR_OUTPUT_TEXT

    def bash_run(command_to_run: str, input: str) -> str:
        res = subprocess.run(command_to_run, stdout=subprocess.PIPE, text=True, input=input)
        if (res.stderr is not None) and (res.stderr != ''):
            print(f"ERROR COMMAND: \'{command_to_run}\'")
            print(res.stderr)
        return res.stdout

    words_list = list(zip(
        words_list,
        cycle((
            r'-e3r',
            r'-e3b',
            r'-e3y',
            r'-e3c',
            r'-e3m',

            r'-e2R',
            r'-e1B',
            r'-e2Y',
            r'-e1C',
            r'-e2M',

            r'-e4r',
            r'-e4b',
            r'-e4y',
            r'-e4c',
            r'-e4m',

        ))
    ))
    # words_list.insert(0, (r'\n\d+: ', ('green', None) ))
    # words_list.insert(0, (r'^\d+: ', ('green', None) ))
    words_list.insert(0, (r'\n[0-9]+: ', r'-e2g'))
    words_list.insert(0, (r'^[0-9]+: ', r'-e2g'))

    hl_command = ["hl"]
    if ignore_case:
        hl_command += ["-i"]
    for i, j in words_list:
        hl_command += [j] + [i]

    if verbose:
        # Print Word Info
        if len(words_list) > 2:
            print("   words = ", end='')
            if COLOR_OUTPUT_TEXT:
                print(
                    ' , '.join([bash_run(f"hl -i {t_color} .*".split(), t_word) for t_word, t_color in words_list[2:]])
                )
                # print(
                #     bash_run(
                #         hl_command,
                #         ' , '.join( [str(i) for i,j in words_list[2:]] )
                #     )
                # )
            else:
                print(' , '.join( [str(i) for i,j in words_list[2:]] ))
        else:
            print("NO words searched")
        # Print Segment Info
        print("segments = " + my_colored(str(len(file_segments_matched)), 'white', attrs=['bold']))

    for i, segment in enumerate(file_segments_matched):
        if COLOR_OUTPUT_TEXT:
            print(
                bash_run(
                    hl_command,
                    segment
                )
            )
        else:
            print(segment)
        if i < len(file_segments_matched) - 1:
            print(my_colored(output_segment_separator, 'white', attrs=['bold']))
        gc.collect()


if __name__ == '__main__':
    # REFER: https://realpython.com/command-line-interfaces-python-argparse/
    import argparse

    # Create the parser
    my_parser = argparse.ArgumentParser(prog='fms.py',
                                        description='Smart multi-word context search across multiples lines',
                                        epilog='Enjoy the program :)',
                                        prefix_chars='-',
                                        fromfile_prefix_chars='@',
                                        allow_abbrev=False,
                                        add_help=True)
    my_parser.version = '2.0'

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
    my_parser.add_argument('-r',
                           '--recursive',
                           action='append',
                           nargs='?',
                           type=str,
                           help='The list of paths to be used for recursive search')
    my_parser.add_argument('-x',
                           '--extensions',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Files with these extensions only to be searched for -r flag (Example Usage: -x md -x pdf OR -x "md pdf") (Note: for "file.tar.gz" only "-x gz" should be used)')
    my_parser.add_argument('-i',
                           '--ignore-case',
                           action='store_true',
                           help='Ignore case while searching')
    my_parser.add_argument('-l',
                           '--files-with-matches',
                           action='store_true',
                           help='Supress normal output and just print the file names which satisfy the search query')
    my_parser.add_argument('-C',
                           metavar='--context',
                           type=int,
                           default=10,
                           help='Number of lines in the context [default: 10]')
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
    my_parser.add_argument('-W',
                           metavar='--Word',
                           action='append',
                           nargs='?',
                           type=str,
                           help='Optional words to search')
    my_parser.add_argument('--color',
                           type=str,
                           default='auto',
                           help="Can either be auto, always or never [default: auto]")
    my_parser.add_argument('-n',
                           '--line-number',
                           action='store_true',
                           help='Print line number (Note: printing line numbers may cause problem -I parameter and REGEX which use "^")')
    my_parser.add_argument('-v',
                           '--verbose',
                           action='store_true',
                           help='Print expression highlighted and number of segments which satisfied the search conditions (Bug: content printed because of this flag will be colored for --color=auto even if the output is not directed to a TTY)')
    my_parser.add_argument('-Q',
                           action='store_true',
                           help='Do not print anything for files in which no results found')
    my_parser.add_argument('-I',
                           '--input-record-separator',
                           action='store',
                           type=str,
                           help='String to separate the input based on the record separator. '
                                'This input will be evaluated as python string. So, to use '
                                'newline followed by two hyphen, just write "\\n--". '
                                'Note: input will be evaluated using python syntax. Hence, no need '
                                'to make bash correctly interpret special characters such as "\\n" or "\\t"')
    my_parser.add_argument('-O',
                           '--output-segment-separator',
                           action='store',
                           type=str,
                           default='--',
                           help='String to separate the output segments which matched the pattern')
    my_parser.add_argument('--cmd',
                           action='store',
                           type=str,
                           help='Command to use to read the input file and to write the output to stdout. '
                                'Insert {} in the command to insert file name, e.g. "pdftotext {} -"')
    my_parser.add_argument('-D',
                           '--debug',
                           action='store_true',
                           help='Print debug information')

    # Execute the parse_args() method
    args: argparse.Namespace = my_parser.parse_args()
    logger = logging.getLogger(__name__)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger_file_handler = logging.FileHandler('/dev/stderr')
    logger_formatter    = logging.Formatter('%(levelname)s :: [%(lineno)s] %(funcName)s :: %(name)s :: %(message)s')
    logger_file_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)

    logger.debug("Debugging is ON")
    logger.debug(args)
    logger.handlers[0].flush()  # REFER: https://stackoverflow.com/questions/13176173/python-how-to-flush-the-log-django/13753911

    if str(args.color).lower() not in ('auto', 'always', 'never'):
        logger.warning('Invalid parameter --color={}'.format(args.color))

    if str(args.color).lower() == 'auto':
        neotermcolor.tty_aware = True
        COLOR_OUTPUT_TEXT = True
    else:
        neotermcolor.tty_aware = False
        if str(args.color).lower() == 'always':
            COLOR_OUTPUT_TEXT = True
        else:
            COLOR_OUTPUT_TEXT = False

    # print('DEBUG: args       = ' + str(args))
    # print('DEBUG: vars(args) = ' + str(vars(args)))
    # print('DEBUG: vars(args) = \n\t\t\t' +
    #       str('\n\t\t\t'.join(['{:30} : {}'.format(i, j) for i, j in vars(args).items()])))

    # REFER: https://stackoverflow.com/questions/6722936/python-argparse-make-at-least-one-argument-required
    # TODO: verify if below condition check is required or not
    # if not (args.g or args.w or args.q):
    #     my_parser.error('No action requested, add -g or -w or -W')

    if args.files_with_matches:
        args.Q = True

    paths_list: List = list()
    if (args.path is None) and (args.Paths is None) and (args.recursive is None):
        paths_list=['/dev/stdin']
    else:
        # Parse -p, -P, -r parameters
        if args.path is not None:
            paths_list.extend(args.path)
        if args.Paths is not None:
            paths_list.extend(args.Paths)
        paths_list.append(None)
        if args.recursive is not None:
            for rec_path in args.recursive:
                # REFER: https://mkyong.com/python/python-how-to-list-all-files-in-a-directory/
                for r,d,f in os.walk(rec_path):
                    for file in sorted(f):
                        paths_list.append(os.path.join(r, file))
        pass

    # Parse -x parameter
    extensions_list: List = None
    if args.extensions is not None:
        if args.recursive is None:
            print('{}: {}'.format(my_colored('Warning', 'yellow', attrs=['bold']), '-x flag will be ignored because -r flag is not used'))
        else:
            extensions_list = list()
            for i in args.extensions:
                for j in i.split():
                    extensions_list.extend(j.lstrip('.'))

    flag_show_directory_warning = True
    flag_check_extensions_list = False
    for input_file_path in paths_list:
        if input_file_path is None:
            flag_check_extensions_list = True
            continue
        file_exists = os.path.exists(input_file_path)
        if not (file_exists):
            print('{}: Cannot open \'{}\' for reading: No such file or directory'.format(my_colored('Warning', 'yellow', attrs=['bold']), my_colored(input_file_path, 'white', attrs=['bold', 'underline'])), file=sys.stderr)
            continue

        if os.path.isdir(input_file_path):
            print('{}: Not scanning directory \'{}\''.format(my_colored('Warning', 'yellow', attrs=['bold']), my_colored(input_file_path, 'white', attrs=['bold', 'underline'])), file=sys.stderr)
            if flag_show_directory_warning:
                print('{}: Use -r for recursively searching inside a directory'.format(my_colored('Warning', 'yellow', attrs=['bold'])), file=sys.stderr)
                flag_show_directory_warning = False
            continue

        if (extensions_list is not None) and flag_check_extensions_list:
            # -x parameter is used
            # Input "example.pdf" ---> ['example', '.pdf']
            # REFER: https://www.geeksforgeeks.org/how-to-get-file-extension-in-python/
            if os.path.splitext(input_file_path)[-1][1:] not in extensions_list:
                continue

        # search_parameters ---> (file_read_command, input_file_path, context_lines, ignore_case, uniq_words_list, input_group_separator_raw)
        search_parameters: Tuple = parse_parameters(parameters=vars(args), input_file_path=input_file_path)
        # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 5, 'w': ['an[a-z]', 'what', 'is', 'o[a-z]'], 'g': None})
        # search_parameters:Dict = parse_parameters({'Path': './Q and A.md', 'ignore_case': True, 'n': 1, 'w': None, 'g': 'an'})

        # print('DEBUG: words_list = ' + str(search_parameters[3]))
        file_segments_matched: List = smart_search(*search_parameters)
        if (args.Q == False) or (len(file_segments_matched) > 0):
            if args.files_with_matches:  # If this is true, then Q flag is set to avoid false +ve
                print(my_colored(input_file_path, 'magenta', attrs=['bold']))
                EXIT_CODE = 0
                continue
            if len(paths_list) > 1:
                print('==> {} <=='.format(my_colored(input_file_path, 'white', attrs=['bold', 'underline'])))

            if len(file_segments_matched) > 0:
                EXIT_CODE = 0
                highlight_words(file_segments_matched=file_segments_matched,
                                words_list=search_parameters[4],
                                ignore_case=search_parameters[3],
                                output_segment_separator=eval("'" + args.output_segment_separator + "'"),
                                verbose=args.verbose)

            if len(paths_list) > 1:
                print()

        gc.collect()
    pass
    sys.exit(EXIT_CODE)
    # Both the EXAMPLE's will give the same result
    # python c-smart-search.py -C 5 -i -g 'an[a-z] what is o[a-z] vms' "./Q and A.md"
    # python c-smart-search.py -C 5 -i -w 'an[a-z]' -w 'what' -w 'is' -w 'o[a-z]' -w 'vms' "./Q and A.md"

    # my     ifconfig | c-fms -C 1000 -W '([a-z]+[0-9]*)+: ' -W '([0-9a-f]{2}:){5}[0-9a-f]{2}' -W '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -W '^(eth|(vir)?br|vnet)[0-9.:]*\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W '(errors|dropped|overruns):[^0][0-9]*'
    # sof    ifconfig | c-fms -C 1000 -W '^(eth|(vir)?br|vnet)[0-9.]*:[0-9]+\>' -W '^(eth|(vir)?br|vnet)[0-9.]*\.[0-9]+\>' -W '([0-9a-f]{2}:){5}[0-9a-f]{2}' -W '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -W '^(eth|(vir)?br|vnet)[0-9.:]*\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W ' (errors|dropped|overruns):[^0][0-9]*'
    # github ifconfig | c-fms -C 1000 -W 'inet addr:([0-9]{1,3}(\.[0-9]{1,3}){3})' -W '^((eth|(vir)?br|vnet)[0-9.]*:[0-9]+)\>' -W '^((eth|(vir)?br|vnet)[0-9.]*\.[0-9]+)\>' -W '(([0-9a-f]{2}:){5}[0-9a-f]{2})' -W '(\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>)' -W '(^(eth|(vir)?br|vnet)[0-9.:]*)\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W ' ((errors|dropped|overruns):[^0][0-9]*)'

    # ip a | c-fms -C 1000 -W '\<((([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]))\>'
    # ps -e | c-fms -C 100000 -W '((0[1-9]|[1-9][0-9])(:[0-9]{2}){2} .*)' -W '(00:00:[1-9][0-9] .*)' -W '(00:(0[1-9]|[1-9][0-9]):[0-9]{2} .*)'
