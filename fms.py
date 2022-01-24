#!/usr/bin/env python3
#!/usr/bin/python3

# Copyright (C) 2021-2022 Fenil Mehta <fenilgmehta@gmail.com>
# All Rights Reserved.

import argparse
import gc
import logging
import math
import os
import pathlib
import re
import subprocess
import sys
import traceback
import urllib.request
from datetime import datetime
from itertools import cycle
from typing import Dict, List, Tuple, Callable, Union

dependencies_missing = False
try:
    import joblib
    import neotermcolor
except:
    dependencies_missing = True

# Multiple Colour Highlighting
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
logger = None
g_EXIT_CODE: int = 1
g_fms_settings: Union['FmsSettings', None] = None
g_fms_cache: Union['FmsCache', None] = None


class FmsSettings:
    def __init__(self):
        self.GROUP_SEPARATOR: str = 'fms_1!2@3#4$5%' + '6^7&8*9(0)_smf'
        self.DEFAULT_EXT_EXCLUDE_LIST: str = 'out exe pkl ttf otf eot jpeg jpg png ppt xlsx 7z rar zip tar gz a ' \
                                             'jar class db mid mp3 mp4 webm mkv ctb ctb~ ctb~~ ctb~~~'

        self.d_debug: bool = False
        self.v_verbose: bool = False
        self.c_color: bool = False

        self.c_context: int = 0

        self.p_paths: List[str] = list()
        self.r_recursives: List[str] = list()
        self.ei_extensions: List[str] = list()
        self.ee_exts_exclude: List[str] = list()

        self.w_words: List[str] = list()
        self.w_words_optional: List[str] = list()
        self.g_group: List[str] = list()
        self.g2_group: List[str] = list()
        self.i_ignore_case: bool = False

        self.c_color_str: str = ''
        self.n_line_number: bool = False
        self.u_url_name: bool = False
        self.l_files_with_matches: bool = False
        self.q_quite: bool = False

        self.i_input_record_separator: str = ''
        self.o_output_segment_separator: str = ''
        self.cmd: str = ''

    def initialize_from_argparse_namespace(self, args: argparse.Namespace):
        # REFER: https://www.studytonight.com/python-howtos/how-to-get-the-home-directory-in-python
        self.cache_path: pathlib.Path = pathlib.Path(pathlib.Path.home()) / '.cache' / 'fms'
        self.d_debug: bool = args.debug
        self.v_verbose: bool = args.verbose

        self.c_context: int = args.C

        self.p_paths: List[str] = args.path
        self.r_recursives: List[str] = args.recursive
        self.ei_extensions: List[str] = args.extensions
        self.ee_exts_exclude: List[str] = args.extexclude

        self.w_words: List[str] = args.w
        self.w_words_optional: List[str] = args.W
        self.g_group: List[str] = args.g
        self.g2_group: List[str] = args.g2
        self.i_ignore_case: bool = args.ignore_case

        self.c_color_str: str = args.color
        self.n_line_number: bool = args.line_number
        self.u_url_name: bool = args.url_name
        self.l_files_with_matches: bool = args.files_with_matches
        self.q_quite: bool = args.Q

        self.i_input_record_separator: str = args.input_record_separator
        self.o_output_segment_separator: str = args.output_segment_separator
        self.cmd: str = args.cmd

        # ---

        global logger
        logger = logging.getLogger(__name__)
        if self.d_debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger_file_handler = logging.FileHandler('/dev/stderr')
        logger_formatter = logging.Formatter('%(levelname)s :: [%(lineno)s] %(name)s :: %(message)s')
        # logger_formatter    = logging.Formatter('%(levelname)s :: [%(lineno)s] %(funcName)s :: %(name)s :: %(message)s')
        logger_file_handler.setFormatter(logger_formatter)
        logger.addHandler(logger_file_handler)

        logger.debug("Debugging is ON")
        logger.debug(type(args))
        logger.debug(args)

        # REFER: https://stackoverflow.com/questions/13176173/python-how-to-flush-the-log-django/13753911
        logger.handlers[0].flush()

        pass


class FmsCache:
    """
    Generate text cache based on (File Absolute Path, File Size in Bytes, Last Modified Time in Nanoseconds)

    Cache Mapping File Content (self.name_mapping_file):
        unique_file_id (Used to assign a unique "cache file name" for each "cached file")
        Key (File Absolute Path) -> Value (
            Entry Creation Date (Useful in finding and deleting obsolete cached data),
            Last Access Date (Updated on each access),
            Tuple[
                File Size in Bytes,
                Last Modified Time in Nanoseconds
            ] (Used to check whether cached data is latest or not),
            Cache File Name (File Name in which cached data is stored using joblib.dump(...))
        )
    """

    def __init__(self, fms_settings: FmsSettings):
        self.fms_settings: FmsSettings = fms_settings
        self.name_mapping_file: pathlib.Path = self.fms_settings.cache_path / "0_name_mapping"

        self.unique_file_id: int = 1
        self.name_mapping: Dict[str, List[datetime.date, datetime.date, Tuple[int, int], str]] = dict()
        self.cache_metadata_updated: bool = False
        if not self.name_mapping_file.parent.exists():
            self.name_mapping_file.parent.mkdir(parents=True)
        pass

    def my_constructor(self) -> None:
        self.cache_metadata_updated = False
        if self.name_mapping_file.exists():
            (self.unique_file_id, self.name_mapping) = joblib.load(self.name_mapping_file)
        else:
            self.unique_file_id = 1
            self.name_mapping = dict()

    def my_destructor(self) -> None:
        if not self.cache_metadata_updated:
            return
        self.cache_metadata_updated = False
        joblib.dump((self.unique_file_id, self.name_mapping), self.name_mapping_file, compress=1)

    @staticmethod
    def get_file_stats(file_path: pathlib.Path) -> Tuple[int, int]:
        """It is assumed that Suffix+FileSizeInBytes+ModifiedTimeInNanoSeconds"""
        # REFER: https://docs.python.org/3/library/pathlib.html#correspondence-to-tools-in-the-os-module
        # REFER: https://stackoverflow.com/questions/2104080/how-can-i-check-file-size-in-python
        #        https://docs.python.org/3/library/os.html#os.stat_result.st_size
        #          st_size = Size of the file in bytes
        #        https://docs.python.org/3/library/os.html#os.stat_result.st_mtime_ns
        #          st_mtime_ns = Time of most recent content modification expressed in nanoseconds as an integer.
        file_stats = file_path.stat()
        return file_stats.st_size, file_stats.st_mtime_ns

    def cache_check_file(self, file_path: pathlib.Path) -> Tuple[bool, bool]:
        """
        Returns 2 booleans
            - False, False - File is not cached
            - True , False - File is cached but not the latest version
            - True , True  - Latest version of the file is cached
        """
        # REFER: https://stackoverflow.com/questions/42513056/how-to-get-absolute-path-of-a-pathlib-path-object
        if (str(file_path.resolve()) in self.name_mapping.keys()) and \
                (self.fms_settings.cache_path / self.name_mapping[str(file_path.resolve())][-1]).exists():
            return True, FmsCache.get_file_stats(file_path) == self.name_mapping[str(file_path.resolve())][2]
        return False, False

    def cache_read_file(self, file_path: pathlib.Path) -> str:
        """
        Call this ONLY if 'cache_check_file(...)' returns:
            - True, False
            - True, True
        """
        self.cache_metadata_updated = True

        # REFER: https://stackoverflow.com/questions/415511/how-to-get-the-current-time-in-python
        self.name_mapping[str(file_path.resolve())][1] = datetime.now().date()  # Update cache entry access date
        return joblib.load(self.fms_settings.cache_path / self.name_mapping[str(file_path.resolve())][-1])

    def cache_write_file(self, file_path: pathlib.Path, data: str) -> None:
        """This will overwrite any old data"""
        self.cache_metadata_updated = True
        entry_creation_date = datetime.now().date()
        file_id: str = str(self.unique_file_id)
        if str(file_path.resolve()) in self.name_mapping.keys():
            val = self.name_mapping[str(file_path.resolve())]
            entry_creation_date = val[0]
            file_id = val[-1]
        else:
            self.unique_file_id += 1
        self.name_mapping[str(file_path.resolve())] = [
            entry_creation_date,
            datetime.now().date(),
            FmsCache.get_file_stats(file_path),
            file_id
        ]
        joblib.dump(data, self.fms_settings.cache_path / file_id, compress=2)


def debug_list(list_var: List, lname: str) -> None:
    print("\n*** *** ***\nDEBUG: " + lname + "\n")
    for i in list_var:
        print(i, end="\n" + GROUP_SEPARATOR + "\n")


def my_colored(text: str, color=None, on_color=None, attrs=None) -> str:
    global COLOR_OUTPUT_TEXT
    if COLOR_OUTPUT_TEXT:
        return neotermcolor.colored(text, color, on_color, attrs)
    return text


def url_to_path(file_path_url: str) -> str:
    if os.path.exists(file_path_url):
        return file_path_url
    # NOTE: Handle quotes in input (this is optional)
    # if os.path.exists(file_path_url[1:-1]):
    #     return file_path_url[1:-1]

    # This primarily converts things like '%20' ---> ' '
    file_url = urllib.request.url2pathname(file_path_url)

    #  0      v index 7
    # "file:///home/student/..."
    file_path = file_url[7:]
    if os.path.exists(file_url):
        file_path = file_url
    if os.path.exists(file_url[1:-1]):  # To handle quotes
        file_path = file_url[1:-1]
    return file_path


def read_file(file_read_command: Union[str, Callable[[str], Tuple[int, str]]],
              input_file_path: str,
              input_group_separator_raw: str,
              add_line_number: bool,
              store_in_cache: bool) -> List:
    cache_status = g_fms_cache.cache_check_file(pathlib.Path(input_file_path))
    # print(f'{store_in_cache=}, {cache_status=}')
    if cache_status[0] == True and (cache_status[1] == True or pathlib.Path(input_file_path).suffix == '.pdf'):
        # NOTE: We read text from cache even if PDF is updated, because generally PDF text is not changed
        #       and only annotations are added to them which cause the cache to feel that the cached data is not latest
        output = g_fms_cache.cache_read_file(pathlib.Path(input_file_path))
    else:
        # print(f'IMP: reading from file')
        if type(file_read_command) == str:
            # Handle single quotes in file name
            # REFER: https://unix.stackexchange.com/questions/187651/how-to-echo-single-quote-when-using-single-quote-to-wrap-special-characters-in
            # REFER: https://stackoverflow.com/questions/1250079/how-to-escape-single-quotes-within-single-quoted-strings
            # print(file_read_command.format("'" + input_file_path.replace(r"'", r"'\''") + "'"))
            status_code, output = subprocess.getstatusoutput(
                file_read_command.format("'" + input_file_path.replace(r"'", r"'\''") + "'")
            )
        else:
            status_code, output = file_read_command(input_file_path)
        output = output.rstrip()

        # REFER: https://unix.stackexchange.com/questions/219438/remove-the-l-aka-f-ff-form-feed-page-break-character
        # output.replace('', '')  # This is to remove the formfeed character
        # output.replace('^L', '')  # This is to remove the formfeed character
        if status_code != 0:
            # ERROR occurred
            print("{}: Unable to read file \'{}\'".format(my_colored('Error', 'red', attrs=['bold']), input_file_path),
                  file=sys.stderr)
            print("{}: status_code = {}".format(my_colored('Error', 'red', attrs=['bold']), str(status_code)),
                  file=sys.stderr)
            print("{}: Output:".format(my_colored('Error', 'red', attrs=['bold'])), file=sys.stderr)
            print(output, file=sys.stderr)
            print("\nExiting...", file=sys.stderr)
            g_fms_cache.my_destructor()
            sys.exit(status_code)

        if store_in_cache:
            g_fms_cache.cache_write_file(pathlib.Path(input_file_path), output)

    if input_group_separator_raw is not None:
        # This "replace" is required because single quotes are used in "eval" statements later
        input_group_separator_raw = input_group_separator_raw.replace("'", r"\'")

    if add_line_number:
        # output_numbered = subprocess.run(['awk', r'''{printf("\033[32m%d:\033[0m %s\n", NR, $0)}''', "-"],
        # TODO: Windows line separator may not work correctly
        line_count = output.count('\n') + 1  # This line count is equal to what Vim shows
        max_digit_count = int(math.log10(line_count)) + 1
        global GROUP_SEPARATOR
        # "-F" parameter is used to avoid un-necessary work by awk to split each line based on spaces
        output_numbered = subprocess.run(
            ['awk', '-F', GROUP_SEPARATOR, r'{printf("%0' + str(max_digit_count) + r'd: %s\n", NR, $0)}', '-'],
            stdout=subprocess.PIPE,
            text=True,
            input=output
        ).stdout
        output_numbered = str(output_numbered)
        # print(output_numbered)
        if input_group_separator_raw is not None:
            if r'\n' in input_group_separator_raw:
                # At present, -n and -I work together properly only if -I has only
                #     1. newline "\n" characters or
                #     2. a simple string without any newline character (regex without "^" and "$" are fine)

                # TODO: This needs to be fixed. It can not handle all splits when "-n" parameter is there
                # TODO: Check if -2 is required or -1 is required
                # NOTE: Previously it was -2
                # NOTE: Last new line need not be replaced
                input_group_separator = eval(
                    "'"
                    + input_group_separator_raw[:-1].replace(r'\n', r'\n\\d+: ')
                    + input_group_separator_raw[-1:]
                    + "'"
                )
                # input_group_separator = eval("'" + input_group_separator_raw.replace(r'\n', r'\n\\d+: ') + "'")
            else:
                # TODO: check this
                # input_group_separator = eval("'" + input_group_separator_raw + "'")
                input_group_separator = eval(r"'\n\\d+: " + input_group_separator_raw + "'")

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
                 add_line_number: bool,
                 store_in_cache: bool) -> List:
    global GROUP_SEPARATOR
    # REFER: https://stackoverflow.com/questions/2168065/how-do-i-get-rid-of-line-separator-when-using-grep-with-context-lines/8840902
    command_to_run = ["grep", "-E", "--color=never", "--group-separator", GROUP_SEPARATOR, "-C", str(context_lines)]
    if ignore_case:
        command_to_run.append("-i")
    # debug_list(words_list, "words_list")
    # group1 = subprocess.check_output(command_to_run + ['-n', words_list[0], input_file_path]).decode("utf-8").strip().split(GROUP_SEPARATOR)
    # eval(...) ensures that '\n' and other special characters are properly interpreted
    group1: List = read_file(file_read_command, input_file_path, input_group_separator_raw, add_line_number,
                             store_in_cache)
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
    input_group_separator_raw = None
    file_extension: str = str(pathlib.Path(input_file_path).suffix).lower()
    file_read_command: str = r'cat --show-nonprinting {}'  # use ^ and M- notation, except for LFD and TAB
    if parameters['cmd'] is not None:
        file_read_command = parameters['cmd']
    elif file_extension == '.pdf':
        file_read_command = r'pdftotext {} -'
    elif file_extension in ('.doc', '.rtf'):
        # TODO: find a better way to extract text from '.rtf'
        # REFER: https://askubuntu.com/a/1140942
        file_read_command = r"catdoc {}"
    elif file_extension in ('.docx', '.dotx', '.docm'):
        # REFER: https://github.com/pzaich/doc_ripper/blob/master/lib/doc_ripper/formats/docx_ripper.rb
        # file_read_command = r"unzip -p {} | grep '<w:t' | sed 's/<[^<]*>//g' | grep -v '^[[:space:]]*$'"
        file_read_command = r"unzip -p {} 'word/document.xml' | sed 's#<w:pPr>#\n#g' | grep '<w:t' | sed 's/<[^<]*>//g'"
        #                              main text^    new line formatting^
        # TODO: compare the below with above
        # REFER: https://stackoverflow.com/questions/5671988/how-to-extract-just-plain-text-from-doc-docx-files
        # REFER: https://stackoverflow.com/questions/15557573/how-to-use-catdoc-to-display-dock-file-encoded-in-utf-8
        # file_read_command = r"unzip -p {} 'word/document.xml' | sed -e 's#<w:pPr>#\n#g' | sed -e 's/<[^>]\{1,\}>//g; s/[^[:print:]]\{1,\}//g'"
        # REFER: https://stackoverflow.com/questions/25228106/how-to-extract-text-from-an-existing-docx-file-using-python-docx
        # Also look at: https://etienned.github.io/posts/extract-text-from-word-docx-simply/
    elif file_extension == '.fodt':
        # REFER: https://stackoverflow.com/questions/5376024/how-to-remove-xml-tags-from-unix-command-line
        file_read_command = r"cat {} | grep '<text:p ' | sed -e 's/<[^>]*>//g'"
    elif file_extension in ('.odt', '.ott'):
        # REFER: https://linuxgazette.net/164/misc/lg/linux_command_to_read_odt.html
        # REFER: https://askubuntu.com/questions/828578/cat-command-doesnt-show-the-lines-of-the-text/828586#828586
        # REFER: https://stackoverflow.com/questions/54293459/find-a-string-in-a-list-of-odt-files-and-print-the-matching-lines
        file_read_command = r"unzip -p {} 'content.xml' | sed -e 's#<text:p text:style-name#\n<text:p text:style-name#g' | sed -e 's/<[^>]*>//g'"
    elif file_extension == '.epub':
        file_read_command = r"unzip -p {} 'OEBPS/sections/section*.xhtml' | sed -e 's# ##g;s#<p #\n<p #g' | sed -e 's/<[^>]*>//g'"
    elif file_extension == '.xlsx':
        file_read_command = r"unzip -p {} 'xl/sharedStrings.xml' | sed -e 's/<si><t/\n<si><t/g' -e 's/<[^>]*>/ /g' -e 's/  / /g' -e 's/  / /g'"
    elif file_extension == '.ods':
        file_read_command = r"unzip -p {} 'content.xml' | sed -e 's/<table:table-row/\n<table:table-row/g' -e 's/<[^>]*>/ /g' -e 's/  / /g' -e 's/  / /g'"
    elif file_extension == '.pptx':
        # REFER: https://superuser.com/questions/661315/tools-to-extract-text-from-powerpoint-pptx-in-linux
        PPT_GROUP_SEPARATOR = r'fms_PPT_' + r'SEPARATOR_smf'

        def read_file_pptx(input_file_path: str):
            global logger
            cmd_slides_list = r"unzip -l '" \
                              + input_file_path.replace(r"'", r"'\''") \
                              + r"' 'ppt/slides/slide*.xml' | awk '{print $4}' | grep 'ppt/slides/slide.*' --color=never | sort -V"
            cmd_read_slide = r"unzip -p '" + input_file_path.replace(r"'", r"'\''") + r"' '{}'"
            status_code, output = subprocess.getstatusoutput(cmd_slides_list)
            if status_code != 0:
                return status_code, ''
            out_slides_list = output.split()
            logger.debug(f'{out_slides_list=}')
            output = ''
            for slide_path in out_slides_list:
                status_code, out_slide = subprocess.getstatusoutput(
                    cmd_read_slide.format(slide_path, slide_path)
                    + r" | grep -oP '(?<=\<a:t\>).*?(?=\</a:t\>)' ; echo '"
                    + PPT_GROUP_SEPARATOR + r"\n'"
                )
                logger.debug(f'{out_slide=}')
                if status_code != 0:
                    output += 'Unable to read slide: {}\n{}\n'.format(slide_path, PPT_GROUP_SEPARATOR)
                else:
                    output += my_colored('Slide ' + slide_path[16:-4], 'white', attrs='bold') + '\n' + out_slide
            return 0, output

        file_read_command = read_file_pptx
        input_group_separator_raw = PPT_GROUP_SEPARATOR
        # Problem with below command is that it does not read the slides in correct order
        # file_read_command = r"unzip -p {} 'ppt/slides/slide*.xml' | grep -oP '(?<=\<a:t\>).*?(?=\</a:t\>)'"
    # .ppt file, REFER: https://askubuntu.com/questions/902877/will-grep-or-sed-search-within-a-ppt-file-to-find-a-phrase
    context_lines: int = parameters['C']
    ignore_case: bool = parameters['ignore_case']

    words_list: List = list()
    if parameters['g'] is not None:
        for i in parameters['g']:
            words_list.extend(list(filter(lambda x: x, i.split())))
            # words_list.extend(i.split())
    if parameters['g2'] is not None:
        for i in parameters['g2']:
            words_list.extend(list(filter(lambda x: x, i.split('  '))))
            # words_list.extend(i.split())
    if parameters['w'] is not None:
        for word in parameters['w']:
            words_list.extend(word)
    if parameters['W'] is not None:
        for i in parameters['W']:
            for word in i:
                words_list.append('({})?'.format(word))

    add_line_number = parameters['line_number']
    words_list_set = set()
    uniq_words_list = list()
    for i in words_list:
        if i in words_list_set:
            continue
        words_list_set.add(i)
        if add_line_number and i[0] == '^':
            # replace "^" with "^([0-9]+: )?" to handle leading line number
            uniq_words_list.append("^([0-9]+: )?(" + i[1:] + ")")
        else:
            uniq_words_list.append(i)

    if input_group_separator_raw is None:
        input_group_separator_raw = parameters['input_record_separator']
    return file_read_command, input_file_path, context_lines, ignore_case, \
           uniq_words_list, input_group_separator_raw, add_line_number, parameters['cache']


def highlight_words(file_segments_matched,
                    words_list: List,
                    ignore_case: bool,
                    output_segment_separator: str,
                    verbose: bool):
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
        # words_list,
        ["({})".format(i) for i in words_list],  # TODO: verify
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
            else:
                print(' , '.join([str(i) for i, j in words_list[2:]]))
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
    if dependencies_missing:
        print("Python dependencies missing, please install joblib and neotermcolor", file=sys.stderr)
        sys.exit(1)

    # Create the parser
    my_parser = argparse.ArgumentParser(prog='fms.py',
                                        description='Smart multi-word context search across multiples lines',
                                        epilog='Enjoy the program :)',
                                        prefix_chars='-',
                                        fromfile_prefix_chars='@',
                                        allow_abbrev=False,
                                        add_help=True)
    my_parser.version = '3.0'

    # DIFFERENCE between Positional and Optional arguments: optional arguments start with - or --, while positional arguments don’t.
    # Add the arguments
    my_parser.add_argument('--version', action='version')
    my_parser.add_argument('-p',
                           '--path',
                           action='append',
                           nargs='+',
                           type=str,
                           help='The path to the text file to search (supports glob)')
    my_parser.add_argument('-r',
                           '--recursive',
                           action='append',
                           nargs='*',
                           type=str,
                           help='The list of paths to be used for recursive search [default: .]')
    # TODO: https://stackoverflow.com/questions/2472221/how-to-check-if-a-file-contains-plain-text/2472243
    # Add -m options for mime type
    # TODO: add comment that -x and -X are matched case insensitive with file extension
    # .a is "current ar archive"
    DEFAULT_EXTEXCLUDE_LIST: str = 'out exe pkl ttf otf eot jpeg jpg png ppt xlsx 7z rar zip tar gz a jar class db ' \
                                   'mid mp3 mp4 webm mkv ctb ctb~ ctb~~ ctb~~~'
    my_parser.add_argument('-X',
                           '--extexclude',
                           action='append',
                           nargs='*',
                           type=str,
                           help='Files with these extensions to be excluded from being searched for -r flag (Example '
                                'Usage: -X tex -X gz OR -x "tex gz") (Note: for "file.tar.gz" only "-X gz" should be '
                                'used) (Note: -X gets priority over -x) (Default exlude list will be used if not ' \
                                'parameters are passed, or "defaults" is passed as '
                                'a parameter: {})'.format(DEFAULT_EXTEXCLUDE_LIST))
    my_parser.add_argument('-x',
                           '--extensions',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Files with these extensions only to be searched for -r flag (Example Usage: -x md '
                                '-x pdf OR -x "md pdf") (Note: for "file.tar.gz" only "-x gz" should be used)')
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
                           default=7,
                           help='Number of lines in the context [default: 7]')
    my_parser.add_argument('-g',
                           metavar='--group',
                           action='append',
                           # nargs='?',
                           type=str,
                           help='Any ONE white space separated group of words to search '
                                '(this gets priority over -w parameter)')
    my_parser.add_argument('-g2',
                           metavar='--group2',
                           action='append',
                           # nargs='?',
                           type=str,
                           help='Any TWO white space separated group of words to search '
                                '(this gets priority over -w parameter)')
    my_parser.add_argument('-w',
                           metavar='--word',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Word to search')
    my_parser.add_argument('-W',
                           metavar='--Word',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Optional words to search')
    my_parser.add_argument('--color',
                           type=str,
                           default='auto',
                           help="Can either be auto, always or never [default: auto]")
    my_parser.add_argument('-u',
                           '--url-name',
                           action='store_true',
                           help='Print clickable file names')
    my_parser.add_argument('-n',
                           '--line-number',
                           action='store_true',
                           help='Print line number (Note: printing line numbers may cause problem -I '
                                'parameter and REGEX which use "^")')
    my_parser.add_argument('-v',
                           '--verbose',
                           action='store_true',
                           help='Print expression highlighted and number of segments which satisfied the '
                                'search conditions (Bug: content printed because of this flag will be '
                                'colored for --color=auto even if the output is not directed to a TTY)')
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
                           help='String to separate the output segments which matched the pattern [default: --]')
    my_parser.add_argument('--cmd',
                           action='store',
                           type=str,
                           help='Command to use to read the input file and to write the output to stdout. '
                                'Insert {} in the command WITHOUT quotes to insert file name, e.g. "pdftotext {} -"')
    my_parser.add_argument('--cache',
                           action='store_true',
                           help='Cache the text content of the files read for better speed in future file reads')
    my_parser.add_argument('-D',
                           '--debug',
                           action='store_true',
                           help='Print debug information')

    # Execute the parse_args() method
    args: argparse.Namespace = my_parser.parse_args()
    g_fms_settings = FmsSettings()
    g_fms_settings.initialize_from_argparse_namespace(my_parser.parse_args())
    g_fms_cache = FmsCache(g_fms_settings)
    g_fms_cache.my_constructor()

    logger = logging.getLogger(__name__)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger_file_handler = logging.FileHandler('/dev/stderr')
    logger_formatter = logging.Formatter('%(levelname)s :: [%(lineno)s] %(name)s :: %(message)s')
    # logger_formatter    = logging.Formatter('%(levelname)s :: [%(lineno)s] %(funcName)s :: %(name)s :: %(message)s')
    logger_file_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)

    logger.debug("Debugging is ON")
    logger.debug(args)
    logger.debug(type(args))
    # REFER: https://stackoverflow.com/questions/13176173/python-how-to-flush-the-log-django/13753911
    logger.handlers[0].flush()

    if str(args.color).lower() not in ('auto', 'always', 'never'):
        logger.warning(
            '{}: Invalid parameter --color={}'.format(my_colored('Warning', 'yellow', attrs=['bold']), args.color)
        )
        logger.warning('         Using --color=auto'.format(args.color))
        args.color = 'auto'

    neotermcolor.tty_aware = False
    if str(args.color).lower() == 'auto':
        # REFER: https://github.com/alttch/neotermcolor/blob/master/neotermcolor/__init__.py
        #        Search "tty_aware" in that file
        COLOR_OUTPUT_TEXT = (os.getenv('ANSI_COLORS_DISABLED') is None) and \
                            (sys.stdout.isatty() and sys.stderr.isatty())
    else:
        if str(args.color).lower() == 'always':
            COLOR_OUTPUT_TEXT = True
        else:  # 'never'
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
    if (args.path is None) and (args.recursive is None):
        paths_list = ['/dev/stdin']
    else:
        # Parse -p, -r parameters
        if args.path is not None:
            for i in args.path:
                paths_list.extend(i)
        paths_list.append(None)
        if args.recursive is not None:
            if [] in args.recursive:
                args.recursive[args.recursive.index([])] = '.'
                args.recursive = list(filter(lambda x: bool(len(x)), args.recursive))
            logger.debug("args.recursive = {}".format(args.recursive))
            set_abs_paths = set()
            for rec_paths_list in args.recursive:
                for rec_path in rec_paths_list:
                    rec_path_abs = os.path.abspath(rec_path)
                    if rec_path_abs in set_abs_paths:
                        print("{}: Skipping duplicate path for -r parameter: '{}'".
                              format(my_colored('Warning', 'yellow', attrs=['bold']), rec_path),
                              file=sys.stderr)
                        continue
                    if os.path.isfile(rec_path_abs):
                        if rec_path_abs not in paths_list:
                            paths_list.append(rec_path_abs)
                        continue
                    set_abs_paths.add(rec_path_abs)
                    # REFER: https://mkyong.com/python/python-how-to-list-all-files-in-a-directory/
                    for r, d, f in os.walk(rec_path):
                        for file in sorted(f):
                            paths_list.append(os.path.join(r, file))
        pass

    # Parse -x parameter
    extensions_list: List = None
    extexclude_list: List = None
    if args.extexclude is not None:
        if (args.recursive is None):
            print('{}: {}'.format(my_colored('Warning', 'yellow', attrs=['bold']),
                                  '-X flag will be ignored because -r flag is not used'))
        else:
            extexclude_list = list()
            if len(args.extexclude) == 1 and len(args.extexclude[0]) == 0:
                # use default exclude list
                extexclude_list.extend(DEFAULT_EXTEXCLUDE_LIST.split())
            else:
                for ext_list in args.extexclude:
                    for ext_multi in ext_list:
                        for ext_i in ext_multi.lower().split():
                            extexclude_list.append(ext_i.lstrip('.'))
                if "defaults" in extexclude_list:
                    extexclude_list.remove("defaults")
                    extexclude_list.extend(DEFAULT_EXTEXCLUDE_LIST.split())
    if args.extensions is not None:
        if args.recursive is None:
            print('{}: {}'.format(my_colored('Warning', 'yellow', attrs=['bold']),
                                  '-x flag will be ignored because -r flag is not used'))
        else:
            extensions_list = list()
            for ext_list in args.extensions:
                for ext_multi in ext_list:
                    for ext_i in ext_multi.lower().split():
                        extensions_list.append(ext_i.lstrip('.'))
            if extexclude_list is not None:
                for ext in extensions_list:
                    if ext in extexclude_list:
                        print(
                            '{}: extention "{}" {} "-x {}"'.format(
                                my_colored('Warning', 'yellow', attrs=['bold']),
                                ext, 'is used with both -x and -X flag. So, ignoring', ext
                            )
                        )

    # Decide which file to use for searching and which
    # not to based on command line parameters
    paths_list_to_process = list()
    flag_show_directory_warning = True
    flag_check_extensions_list = False
    for input_file_path in paths_list:
        if input_file_path is None:
            # not we start performing -x flag based filtering
            # because from now on, the files fetched because
            # of -r flag are present in the list "paths_list"
            flag_check_extensions_list = True
            continue
        if not os.path.exists(input_file_path):
            input_file_path = url_to_path(input_file_path)
        if not os.path.exists(input_file_path):
            # "input_file_path" does NOT exist
            print(
                '{}: Cannot open \'{}\' for reading: No such file or directory'.format(
                    my_colored('Warning', 'yellow', attrs=['bold']),
                    my_colored(input_file_path, 'white', attrs=['bold', 'underline'])
                ),
                file=sys.stderr
            )
            continue
        if os.path.isdir(input_file_path):
            # "input_file_path" is a directory, NOT a file
            print(
                '{}: Not scanning directory \'{}\''.format(
                    my_colored('Warning', 'yellow', attrs=['bold']),
                    my_colored(input_file_path, 'white', attrs=['bold', 'underline'])
                ),
                file=sys.stderr
            )
            if flag_show_directory_warning:
                print(
                    '{}: Use -r for recursively searching inside a directory'.format(
                        my_colored('Warning', 'yellow', attrs=['bold'])
                    ),
                    file=sys.stderr
                )
                flag_show_directory_warning = False
            continue

        # Input "example.pdf" ---> ['example', '.pdf']
        # REFER: https://www.geeksforgeeks.org/how-to-get-file-extension-in-python/
        if flag_check_extensions_list and (extexclude_list is not None):
            # -X parameter is used
            if os.path.splitext(input_file_path)[-1][1:].lower() in extexclude_list:
                continue
        if flag_check_extensions_list and (extensions_list is not None):
            # -x parameter is used
            if os.path.splitext(input_file_path)[-1][1:] not in extensions_list:
                continue
        paths_list_to_process.append(input_file_path)

    logger.debug("extensions_list         = {}".format(extensions_list))
    logger.debug("extexclude_list         = {}".format(extexclude_list))
    logger.debug("paths_list_to_process   = {}".format(paths_list_to_process))
    set_abs_filepaths = set()
    for input_file_path in paths_list_to_process:
        input_file_path_abs = os.path.abspath(input_file_path)
        if input_file_path_abs in set_abs_filepaths:
            continue  # skip duplicate file during searching
        set_abs_filepaths.add(input_file_path_abs)

        try:
            # search_parameters ---> (file_read_command, input_file_path, context_lines, ignore_case, uniq_words_list, input_group_separator_raw, add_line_number)
            search_parameters: Tuple = parse_parameters(parameters=vars(args), input_file_path=input_file_path)

            for var_value, var_name in zip(search_parameters,
                                           ["file_read_command", "input_file_path", "context_lines", "ignore_case",
                                            "uniq_words_list", "input_group_separator_raw", "add_line_number"]):
                logger.debug("{:<20s} = {}".format(var_name, var_value))

            file_segments_matched: List = smart_search(*search_parameters)
        except Exception as e:
            logger.error('File ==> {} <=='.format(my_colored(input_file_path, 'white', attrs=['bold', 'underline'])))
            logger.error(e)
            logger.error(traceback.format_exc())
            print()
            continue

        if (args.Q == False) or (len(file_segments_matched) > 0):
            if args.files_with_matches:  # If this is true, then Q flag is set to avoid false +ve
                print(my_colored(input_file_path, 'magenta', attrs=['bold']))
                g_EXIT_CODE = 0
                continue
            if len(paths_list_to_process) > 1:
                if args.url_name:
                    # REFER: https://stackoverflow.com/questions/11687478/convert-a-filename-to-a-file-url
                    print(
                        '==> {} <=='.format(
                            my_colored(
                                pathlib.Path(input_file_path).absolute().as_uri(),
                                'white',
                                attrs=['bold', 'underline']
                            )
                        )
                    )
                else:
                    print('==> {} <=='.format(my_colored(input_file_path, 'white', attrs=['bold', 'underline'])))

            if len(file_segments_matched) > 0:
                g_EXIT_CODE = 0
                try:
                    highlight_words(file_segments_matched=file_segments_matched,
                                    words_list=search_parameters[4],
                                    ignore_case=search_parameters[3],
                                    output_segment_separator=eval("'" + args.output_segment_separator + "'"),
                                    verbose=args.verbose)
                except BrokenPipeError as e:
                    logger.debug(
                        f'Output was piped to something which was closed before '
                        f'`fms` finished writing everything to the stream'
                    )
                    logger.debug(f'{e}')
                    logger.debug(traceback.format_exc())
            if len(paths_list_to_process) > 1:
                print()

        gc.collect()
    pass
    logger.debug("g_EXIT_CODE = {}".format(g_EXIT_CODE))
    g_fms_cache.my_destructor()
    sys.exit(g_EXIT_CODE)

    # BEST WORKING
    # ps -e | fms -C 100000 -W '((0[1-9]|[1-9][0-9])(:[0-9]{2}){2} .*)' -W '(00:00:[1-9][0-9] .*)' -W '(00:(0[1-9]|[1-9][0-9]):[0-9]{2} .*)'
    # ip a | fms -C100000 -W '\<((([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]))\>' -W '(^[0-9]+: )(\d|\w+)'
    # my     ifconfig | fms -C 1000 -W '([a-z]+[0-9]*)+: ' -W '([0-9a-f]{2}:){5}[0-9a-f]{2}' -W '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -W '^(eth|(vir)?br|vnet)[0-9.:]*\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W '(errors|dropped|overruns):[^0][0-9]*'
    # sof    ifconfig | fms -C 1000 -W '^(eth|(vir)?br|vnet)[0-9.]*:[0-9]+\>' -W '^(eth|(vir)?br|vnet)[0-9.]*\.[0-9]+\>' -W '([0-9a-f]{2}:){5}[0-9a-f]{2}' -W '\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>' -W '^(eth|(vir)?br|vnet)[0-9.:]*\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W ' (errors|dropped|overruns):[^0][0-9]*'
    # github ifconfig | fms -C 1000 -W 'inet addr:([0-9]{1,3}(\.[0-9]{1,3}){3})' -W '^((eth|(vir)?br|vnet)[0-9.]*:[0-9]+)\>' -W '^((eth|(vir)?br|vnet)[0-9.]*\.[0-9]+)\>' -W '(([0-9a-f]{2}:){5}[0-9a-f]{2})' -W '(\<UP\>|\<RUNNING\>|([0-9]{1,3}\.){3}[0-9]{1,3}\>)' -W '(^(eth|(vir)?br|vnet)[0-9.:]*)\>' -W '[0-9a-f]{4}::[0-9a-f]{4}\:[0-9a-f]{4}:[0-9a-f]{4}:[0-9a-f]{4}' -W ' ((errors|dropped|overruns):[^0][0-9]*)'

    # This   # echo "abcdefghijklmnopqrstuvwxyz" | fms -g "a b c d e f g h i j k l n o p q r s t u v w x y z"
    # Link 1 # echo "abcdefghijklmnopqrstuvwxyz" | rpen.py -k a b c d e f g h i j k l n o p q r s t u v w x y z
    # Link 2 # echo "abcdefghijklmnopqrstuvwxyz" | h a b c d e f g h i j k l n
