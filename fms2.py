#!/usr/bin/env python3
# REFER: https://unix.stackexchange.com/a/29611
# REFER: https://unix.stackexchange.com/questions/12736/how-does-usr-bin-env-know-which-program-to-use/12751#12751

# Copyright (C) 2021-2022 Fenil Mehta <fenilgmehta@gmail.com>
# All Rights Reserved.

import argparse
import atexit
import errno
import io
import logging
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime
from typing import Union, Tuple, List, Dict

dependencies_missing = False
try:
    import joblib  # Only required for FmsCache
    import magic  # Check file type

    # REFER: https://github.com/willmcgugan/rich/
    import rich
    from rich.logging import RichHandler

    # REFER: https://github.com/tartley/colorama/
    import colorama  # Print colourful text (cross-platform)
    import neotermcolor

    colorama.init(strip=(platform.system() == 'Windows'))

    # NOTE: The Apache Tika toolkit detects and extracts metadata and text from over
    #       a thousand different file types (such as PDF, DOC, PPT, XLS, ...)
    #       REFER: https://stackoverflow.com/questions/34837707/how-to-extract-text-from-a-pdf-file
    #       REFER: https://github.com/chrismattmann/tika-python
    #       REFER: https://github.com/apache/tika
    #              https://tika.apache.org/1.10/formats.html
    # NOTE: Access Java classes from Python
    #       REFER: https://github.com/kivy/pyjnius
    # NOTE: Other python lib for same task but provide limited functionalities
    #       REFER: https://github.com/deanmalmgren/textract/
    #              https://textract.readthedocs.io/en/latest/python_package.html
    from tika import parser as tika_parser
except:
    print("Please install python library dependencies using:\n\tpip install -r requirements.txt", file=sys.stderr)
    dependencies_missing = True

g_IS_WINDOWS: bool = (platform.system() == 'Windows')
g_logger: Union[logging.Logger, None] = None
g_fms_settings: Union['FmsSettings', None] = None
g_EXIT_CODE: int = 0


def my_colored(text: str, color=None, on_color=None, attrs=None) -> str:
    global g_fms_settings, g_logger
    if g_fms_settings.color_bool:
        return neotermcolor.colored(text, color, on_color, attrs)
        # res = ''
        # if color is not None:
        #     res += eval(f'"colorama.Fore.{color.upper()}"')
        # if on_color is not None:
        #     res += eval(f'"colorama.Back.{color.upper()}"')
        # if type(attrs) is not List:
        #     attrs = [attrs]
        # for i in attrs:
        #     if i == 'bold':
        #         res += colorama.Style.BRIGHT
        #     elif i == 'dim':
        #         res += colorama.Style.DIM
        #     else:
        #         g_logger.error(f'Incorrect value in attrs="{i}"')
        # return res + text + colorama.Style.RESET_ALL
    return text


class FmsSettings:
    GROUP_SEPARATOR: str = 'fms_1!2@3#4$5%' + '6^7&8*9(0)_smf'

    # .a is "current ar archive", is a "static library" created with the `ar` utility
    DEFAULT_EXT_EXCLUDE_LIST: str = 'out exe pkl ttf otf eot 7z rar zip tar gz a jar class db ' \
                                    'mid mp3 mp4 webm mkv ctb ctb~ ctb~~ ctb~~~'

    def __init__(self):
        self.c_context: int = 0

        self.p_paths: List[str] = list()
        self.r_recursives: List[str] = list()
        self.ei_extensions: List[str] = list()
        self.ei_extensions_add: List[str] = list()
        self.ee_extensions_exclude: List[str] = list()
        self.ee_extensions_exclude_subtract: List[str] = list()

        self.g_group: List[str] = list()
        self.g2_group: List[str] = list()
        self.w_words: List[str] = list()
        self.w_words_optional: List[str] = list()

        self.i_ignore_case: bool = False
        self.n_line_number: bool = False
        self.l_files_with_matches: bool = False
        self.q_quiet: bool = False
        self.u_url_name: bool = False
        self.color_str: str = ''
        self.color_bool: bool = False  # extra

        self.o_output_segment_separator: str = ''
        self.cmd: str = ''

        self.cache: bool = False
        self.cache_path: str = ''  # extra

        self.verbose: bool = False
        self.debug: bool = False

    def initialize_from_argparse_namespace(self, args: argparse.Namespace):
        global g_IS_WINDOWS

        self.c_context: int = args.context

        self.p_paths: List[str] = args.path
        self.r_recursives: List[str] = args.recursive
        self.ei_extensions: List[str] = args.extensions
        self.ei_extensions_add: List[str] = args.extensions_add
        self.ee_extensions_exclude: List[str] = args.extensions_exclude
        self.ee_extensions_exclude_subtract: List[str] = args.extensions_exclude_subtract

        self.g_group: List[str] = args.group
        self.g2_group: List[str] = args.group2
        self.w_words: List[str] = args.word
        self.w_words_optional: List[str] = args.Word

        self.i_ignore_case: bool = args.ignore_case
        self.n_line_number: bool = args.line_number
        self.l_files_with_matches: bool = args.files_with_matches
        self.q_quiet: bool = args.quiet
        self.u_url_name: bool = args.url_name
        self.color_str: str = args.color

        self.o_output_segment_separator: str = args.output_segment_separator
        self.cmd: str = args.cmd

        self.cache: bool = args.cache

        self.verbose: bool = args.verbose
        self.debug: bool = args.debug

        g_logger.debug(f'Debugging is {"ON" if self.debug else "OFF"}')
        g_logger.debug(type(args))
        g_logger.debug(args)

    def initialize_data(self) -> None:
        """Call this after setting all the command line parameters as variables of this class"""
        global g_logger, g_IS_WINDOWS
        if self.debug:
            g_logger.setLevel(logging.DEBUG)
        else:
            g_logger.setLevel(logging.INFO)
        if g_IS_WINDOWS:
            # NOTE: This can be used for Linux as well
            # REFER: https://www.tutorialspoint.com/generate-temporary-files-and-directories-using-python
            # REFER: https://stackoverflow.com/questions/42513056/how-to-get-absolute-path-of-a-pathlib-path-object
            logger_file_handler = logging.FileHandler(
                (pathlib.Path(tempfile.gettempdir()) / 'fms_stderr.log').resolve())
        else:
            logger_file_handler = logging.FileHandler('/dev/stderr')
        logger_formatter = logging.Formatter('%(levelname)s :: [%(lineno)s] %(name)s :: %(message)s')
        # logger_formatter    = logging.Formatter('%(levelname)s :: [%(lineno)s] %(funcName)s :: %(name)s :: %(message)s')
        logger_file_handler.setFormatter(logger_formatter)
        g_logger.addHandler(logger_file_handler)

        # REFER: https://stackoverflow.com/questions/13176173/python-how-to-flush-the-log-django/13753911
        g_logger.handlers[0].flush()

        # ---

        # REFER: https://www.studytonight.com/python-howtos/how-to-get-the-home-directory-in-python
        # REFER: https://stackoverflow.com/questions/22947427/getting-home-directory-with-pathlib
        # REFER: https://www.freecodecamp.org/news/appdata-where-to-find-the-appdata-folder-in-windows-10/
        #        The Local folder is used to store data that is specific to a single windows system,
        #        which means data is not synced between multiple PCs.
        self.cache_path: pathlib.Path = pathlib.Path(pathlib.Path.home()) / '.cache' / 'fms'
        if g_IS_WINDOWS:
            self.cache_path = pathlib.Path(pathlib.Path.home()) / 'AppData' / 'Local' / 'fms'
        self.cache_path: str = self.cache_path.resolve()
        # REFER: https://www.tutorialspoint.com/How-can-I-create-a-directory-if-it-does-not-exist-using-Python
        try:
            os.makedirs(self.cache_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                g_logger.error(f"{type(e)=}, {e=}")
                raise  # This will re-raise the last exception that was active

        # TODO
        pass


# NOTE: Tika is all in one solution :)
# TODO: Read more at https://www.lesbonscomptes.com/recoll/pages/features.html#doctypes
# TODO: https://github.com/Genivia/ugrep
#   Look at `pandoc` to convert .docx, .epub, and other document formats
#   Look at `soffice` for office documents
#   For excel files, look at https://csvkit.readthedocs.io/en/latest/tutorial/1_getting_started.html#in2csv-the-excel-killer
class ReadAnyFile:
    @staticmethod
    def run_command_get_output(cmd: str, file_path: str) -> Tuple[int, str]:
        """The command "cmd" must have {} at the place where file path is to be used"""
        # Handle single quotes in file name
        # REFER: https://unix.stackexchange.com/questions/187651/how-to-echo-single-quote-when-using-single-quote-to-wrap-special-characters-in
        # REFER: https://stackoverflow.com/questions/1250079/how-to-escape-single-quotes-within-single-quoted-strings
        try:
            status_code, output = subprocess.getstatusoutput(
                cmd.format("'" + file_path.replace(r"'", r"'\''") + "'")
            )
            return status_code, output
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
        return -1, ""

    @staticmethod
    def read_pdf(file_path: str) -> Tuple[int, str]:
        # PDF used for testing https://arxiv.org/abs/2007.14521
        #     - Check page 3 of the PDF. The paragraph containing the line "This is the second" and the paragraph
        #       after it were used for comparing the order.

        # METHODs
        # Tika: Apache Java Library
        #     - This is the BEST as compared to the below techniques.
        #     - Correct order of paragraphs, and proper splitting of words and lines.
        #     - Parsed annotations as well.
        # pdftotext: Command line tool (sudo apt install) (used in old `fms`)
        #     - The order of content was not perfect. It was as thought we did CTRL+A and CTRL+C to get the text.
        #     - Did NOT parse annotations.
        #     - Recoll app uses this (Text extraction of "Rivet research paper" PDF was same as that of `pdftotext`)
        # PyPDF2 and PyPDF4: Python Lib (pip install)
        #     - https://github.com/mstamy2/PyPDF2
        #     - https://github.com/claird/PyPDF4
        #     - The order of paragraphs was better than `pdftotext`
        #     - Did NOT parse annotations.
        #     - Did NOT parse the PDF properly. No space between words, Random splitting of words across lines.
        # pdftotext: Python Lib (pip install pdftotext)
        #     - https://github.com/jalan/pdftotext
        #     - The order of paragraphs was a mix of `pdftotext` command and `PyPDF(2|4)` python lib.
        #       The output some what looked like looking pdf on terminal (two columns were there like in PDF viewer)
        #     - Did NOT parse annotations
        return ReadAnyFile.run_command_get_output(r'pdftotext {} -', file_path)

    @staticmethod
    def read_doc(file_path: str) -> Tuple[int, str]:
        # File used for testing https://github.com/abhinaba-ghosh/any-text/blob/master/test/files/dummy.doc

        # METHODs
        # 1. Tika: Apache Java Library
        #     - Overall good
        #     - Did not parse hyperlinks inside words
        # 2. catdoc: Command line tool (sudo apt install) (used in old `fms`)
        #     - Would parse hyperlinks inside words
        #     - Would NOT parse numbers/bullet points in lists
        # 3. Recoll: Application
        #     - When opened the doc in Okular app, it seemed to render the same thing
        # 4. CTRL+A, CTRL+C: Manual way

        # TODO: find a better way to extract text from '.rtf'
        # REFER: https://askubuntu.com/a/1140942
        return ReadAnyFile.run_command_get_output(r'catdoc {}', file_path)

    # REUSE another file format reader
    @staticmethod
    def read_rtf(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.read_doc(file_path)

    @staticmethod
    def read_docx(file_path: str) -> Tuple[int, str]:
        # # Python Equivalent of OLD Method (command line technique)
        # a = zipfile.ZipFile(file_path,'r')
        # b = a.open('word/document.xml')
        # c = b.read()
        c = zipfile.ZipFile(file_path, 'r').open('word/document.xml').read()
        d = re.sub(r'<w:pPr>', '\n', c.decode())
        e = list(filter(lambda x: r'<w:t' in x, d.splitlines()))
        f = [re.sub(r'<[^<]*>', '', i) for i in e]
        return 0, '\n'.join(f)

        # # OLD Method
        # # REFER: https://github.com/pzaich/doc_ripper/blob/master/lib/doc_ripper/formats/docx_ripper.rb
        # # file_read_command = r"unzip -p {} | grep '<w:t' | sed 's/<[^<]*>//g' | grep -v '^[[:space:]]*$'"
        # return ReadAnyFile.run_command_get_output(
        #     r"unzip -p {} 'word/document.xml' | sed -e 's#<w:pPr>#\n#g' | grep '<w:t' | sed 's/<[^<]*>//g'",
        #     #          main text^    new line formatting^
        #     file_path
        # )

        # # The text output of below method is same as the above method. However, there is difference of
        # # few spaces and new line characters
        # # REFER: https://stackoverflow.com/questions/5671988/how-to-extract-just-plain-text-from-doc-docx-files
        # # REFER: https://stackoverflow.com/questions/15557573/how-to-use-catdoc-to-display-dock-file-encoded-in-utf-8
        # file_read_command = r"unzip -p {} 'word/document.xml' | sed -e 's#<w:pPr>#\n#g' | sed -e 's/<[^>]\{1,\}>//g; s/[^[:print:]]\{1,\}//g'"
        # # REFER: https://stackoverflow.com/questions/25228106/how-to-extract-text-from-an-existing-docx-file-using-python-docx
        # # Also look at: https://etienned.github.io/posts/extract-text-from-word-docx-simply/
        pass

    # REUSE another file format reader
    @staticmethod
    def read_dotx(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.read_docx(file_path)

    # REUSE another file format reader
    @staticmethod
    def read_docm(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.read_docx(file_path)

    @staticmethod
    def read_fodt(file_path: str) -> Tuple[int, str]:
        # REFER: https://stackoverflow.com/questions/5376024/how-to-remove-xml-tags-from-unix-command-line
        return ReadAnyFile.run_command_get_output(r"cat {} | grep '<text:p ' | sed -e 's/<[^>]*>//g'", file_path)

    @staticmethod
    def read_odt(file_path: str) -> Tuple[int, str]:
        # REFER: https://linuxgazette.net/164/misc/lg/linux_command_to_read_odt.html
        # REFER: https://askubuntu.com/questions/828578/cat-command-doesnt-show-the-lines-of-the-text/828586#828586
        # REFER: https://stackoverflow.com/questions/54293459/find-a-string-in-a-list-of-odt-files-and-print-the-matching-lines
        return ReadAnyFile.run_command_get_output(
            r"unzip -p {} 'content.xml' | "
            r"sed -e 's#<text:p text:style-name#\n<text:p text:style-name#g' | "
            r"sed -e 's/<[^>]*>//g'",
            file_path
        )

    # REUSE another file format reader
    @staticmethod
    def read_ott(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.read_odt(file_path)

    @staticmethod
    def read_epub(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.run_command_get_output(
            r"unzip -p {} 'OEBPS/sections/section*.xhtml' | sed -e 's# ##g;s#<p #\n<p #g' | sed -e 's/<[^>]*>//g'",
            file_path
        )

    @staticmethod
    def read_xlsx(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.run_command_get_output(
            r"unzip -p {} 'xl/sharedStrings.xml' | sed -e 's/<si><t/\n<si><t/g' -e 's/<[^>]*>/ /g' -e 's/  / /g' -e 's/  / /g'",
            file_path
        )

    @staticmethod
    def read_ods(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.run_command_get_output(
            r"unzip -p {} 'content.xml' | sed -e 's/<table:table-row/\n<table:table-row/g' -e 's/<[^>]*>/ /g' -e 's/  / /g' -e 's/  / /g'",
            file_path
        )

    @staticmethod
    def read_pptx(file_path: str) -> Tuple[int, str]:
        # REFER: https://superuser.com/questions/661315/tools-to-extract-text-from-powerpoint-pptx-in-linux
        PPT_GROUP_SEPARATOR = r'fms_PPT_' + r'SEPARATOR_smf'

        def read_file_pptx(input_file_path: str) -> Tuple[int, str]:
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

        status_code, output = read_file_pptx(file_path)
        # TODO: Think about how to use this just like commit "2e7e8df7e80781f05a9c21e92174aafc69d24c53"
        #       Below statement is the temporary solution
        # input_group_separator_raw = PPT_GROUP_SEPARATOR
        return status_code, output.replace(PPT_GROUP_SEPARATOR, '\n\n').strip()

        # Problem with below command is that it does not read the slides in correct order
        # file_read_command = r"unzip -p {} 'ppt/slides/slide*.xml' | grep -oP '(?<=\<a:t\>).*?(?=\</a:t\>)'"
        pass

    @staticmethod
    def read_ppt(file_path: str) -> Tuple[int, str]:
        # .ppt file
        # REFER: https://askubuntu.com/questions/902877/will-grep-or-sed-search-within-a-ppt-file-to-find-a-phrase
        raise NotImplementedError

    @staticmethod
    def read_txt(file_path: str) -> Tuple[int, str]:
        return ReadAnyFile.run_command_get_output(r'cat {}', file_path)

    @staticmethod
    def is_text_file(file_path: str) -> bool:
        # REFER: https://stackoverflow.com/questions/2472221/how-to-check-if-a-file-contains-plain-text/2472243
        # REFER: https://stackoverflow.com/questions/43580/how-to-find-the-mime-type-of-a-file-in-python
        # Example:
        #   file.md -> text/plain
        #   file.py -> text/x-python
        # TODO: Not sure whether to use "in" or "=="
        # return 'text' in magic.from_file(file_path, mime=True)
        return 'text' == magic.from_file(file_path, mime=True)[:4].lower()

    @staticmethod
    def can_read_generic(file_path: str) -> bool:
        # NOTE: We use suffix[1:] because the first letter will be a dot ('.')
        file_extension: str = str(pathlib.Path(file_path).suffix).lower()[1:]
        can_read: bool = file_extension in 'pdf doc rtf docx dotx docm fodt odt ott epub xlsx ods pptx'.split()
        return can_read or ReadAnyFile.is_text_file(file_path)

    @staticmethod
    def read_generic(file_path: str) -> str:
        if ReadAnyFile.is_text_file(file_path):
            status_code, output = ReadAnyFile.read_txt(file_path)
        else:
            file_extension: str = str(pathlib.Path(file_path).suffix).lower()
            status_code, output = eval(f'ReadAnyFile.read_{file_extension[1:]}')(file_path)

        if status_code == 0:
            return output

        global logger
        # ERROR occurred
        print("{}: Unable to read file \'{}\'".format(my_colored('Error', 'red', attrs='bold'), file_path),
              file=sys.stderr)
        print("{}: status_code = {}".format(my_colored('Error', 'red', attrs='bold'), str(status_code)),
              file=sys.stderr)
        print("{}: Output:".format(my_colored('Error', 'red', attrs='bold')), file=sys.stderr)
        print(output, file=sys.stderr)
        print("\nExiting...", file=sys.stderr)
        sys.exit(status_code)

    # ---

    # For Apache Tika v1.28
    # REFER: https://repo1.maven.org/maven2/org/apache/tika/tika-server/1.28/tika-server-1.28-bin.zip
    #        README.md file inside this zip
    # REFER: https://cwiki.apache.org/confluence/display/TIKA/TikaServer#:~:text=resources%20may%20return
    # -----------------
    # HTTP Return Codes
    #   `200` - Ok
    #   `204` - No content (for example when we are unpacking file without attachments)
    #   `415` - Unknown file type
    #   `422` - Unparsable document of known type (password protected documents and unsupported versions like Biff5 Excel)
    #   `500` - Internal error
    TIKA_STATUS_CODES: Dict[int, str] = {
        200: 'Ok - request completed sucessfully',
        204: 'No content - request completed sucessfully, result is empty (for example when we are unpacking file without attachments)',
        415: 'Unknown file type',
        422: 'Unparsable document of known type (for example password protected'
             ' documents and unsupported versions like Biff5 Excel)',
        500: 'Error - Error while processing document (Internal error)'
    }
    DEFAULT_LIST_2: str = 'text pdf doc docx xls xlsx ppt pptx odt ods odp epub jpg png ' \
                          'rtf dotx docm fodt ott'

    # REFER: https://stackoverflow.com/questions/39921087/a-openfile-r-a-readline-output-without-n
    # REFER: https://docs.python.org/2/library/io.html?highlight=io.open#io.open
    # REFER: https://stackoverflow.com/questions/17949508/python-read-all-text-file-lines-in-loop
    # REFER: https://stackoverflow.com/questions/19151/how-to-build-a-basic-iterator
    class TextFileReader:
        def __init__(self, file_path: str):
            self.file_path = file_path
            self.f: Union[None, io.TextIOWrapper] = None

        def __iter__(self):
            self.f = io.open(file=self.file_path, mode='rt', newline=None)
            return self

        def __next__(self):
            line = self.f.readline()
            if line == '':  # File has been completely read, EOF has been reached
                raise StopIteration
            if line[-1] == '\n':
                return line[:-1]
            else:
                return line

    @staticmethod
    def can_read_generic_2(file_path: str) -> bool:
        # NOTE: We use suffix[1:] because the first letter will be a dot ('.')
        file_extension: str = str(pathlib.Path(file_path).suffix).lower()[1:]
        can_read: bool = file_extension in ReadAnyFile.DEFAULT_LIST_2.split()
        return can_read or ReadAnyFile.is_text_file(file_path)

    @staticmethod
    def read_generic_2(file_path: str) -> Union['ReadAnyFile.TextFileReader', List[str]]:
        if ReadAnyFile.is_text_file(file_path):
            return ReadAnyFile.TextFileReader(file_path)

        res = tika_parser.from_file(file_path, service='text', xmlContent=True)
        if res['status'] == 200:
            # In[75] : 'a\n\nb\n'.splitlines(keepends=False)  # This is the default
            # Out[75]: ['a', '', 'b']
            # In[76] : 'a\n\nb\n'.splitlines(keepends=True)
            # Out[76]: ['a\n', '\n', 'b\n']
            if res['content'] is None:
                return ['']
            return re.sub('\n(\\s*\n)+', '\n\n', res['content'].strip()).splitlines(keepends=False)

        # else:
        global g_logger
        g_logger.error(f'file_path="{file_path}", '
                       f'status={res["status"]}, reason={ReadAnyFile.TIKA_STATUS_CODES[res["status"]]}')
        return ['']


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

    def cache_clean(self) -> None:
        # TODO: clear the full cache
        pass

    def cache_purge(self, days: int = 31) -> None:
        # TODO: delete cache which was last access before `days` number of days
        pass


def my_main():
    global g_IS_WINDOWS, g_fms_settings
    # REFER: https://realpython.com/command-line-interfaces-python-argparse/
    # REFER: https://stackoverflow.com/questions/19124304/what-does-metavar-and-action-mean-in-argparse-in-python
    # Create the parser

    # NOTE: `cmd_prefix` is used to provide command line parameter '-h' and '/h' on Linux and Windows respectively
    cmd_prefix = '-'
    # REFER: https://docs.python.org/3/library/platform.html#platform.system
    if g_IS_WINDOWS:
        cmd_prefix = '/'

    my_parser = argparse.ArgumentParser(prog='fms.py',
                                        description='Smart multi-word search across multiples lines',
                                        epilog='Enjoy the program :)',
                                        prefix_chars=cmd_prefix,
                                        fromfile_prefix_chars='@',
                                        allow_abbrev=False,
                                        add_help=True)
    my_parser.version = '3.1'

    # DIFFERENCE between Positional and Optional arguments
    #     Optional arguments start with - or --, while Positional arguments don't

    # Add the arguments
    my_parser.add_argument('--version', action='version')

    my_parser.add_argument('-C',
                           '--context',
                           metavar="CONTEXT_LINE_RANGE",
                           action='store',
                           type=int,
                           default=7,
                           help='Number of consecutive lines which should satisfy the query-words [default: 7]')

    my_parser.add_argument('-p',
                           '--path',
                           action='append',
                           nargs='+',
                           type=str,
                           help='The path to the file to search')
    my_parser.add_argument('-r',
                           '--recursive',
                           action='append',
                           nargs='+',
                           type=str,
                           help='The list of paths to be used for recursive search')

    # TODO: Add -m options for mime type (optional, not sure if such an option is required or not)
    # TODO: Add comment that -x and -X are matched case insensitive with file extension
    my_parser.add_argument('-x',
                           '--extensions',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Files with these extensions only to be searched for -r flag • (Example Usage: -x md '
                                '-x pdf OR -x "md pdf") • (Note: for "file.tar.gz" only "-x gz" should be used)')
    my_parser.add_argument('-X',
                           '--extensions-add',
                           action='append',
                           nargs='+',
                           type=str,
                           help=f'DEFAULT_LIST ({ReadAnyFile.DEFAULT_LIST_2}) + '
                                f'Files with these extensions to be searched for -r flag')
    my_parser.add_argument('-y',
                           '--extensions-exclude',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Files with these extensions to be excluded from being searched for -r flag • (Example '
                                'Usage: -y tex -y gz OR -y "tex gz") • (Note: for "file.tar.gz" only "-y gz" should be '
                                'used) • (Note: -y gets priority over -x and -X) • (Default exclude list will be used '
                                'if no parameters are passed, or "defaults" is passed as '
                                'a parameter: {})'.format(FmsSettings.DEFAULT_EXT_EXCLUDE_LIST))
    my_parser.add_argument('-Y',
                           '--extensions-exclude-subtract',
                           action='append',
                           nargs='+',
                           type=str,
                           help=f'DEFAULT_LIST ({ReadAnyFile.DEFAULT_LIST_2}) - '
                                f'Files with these extensions to be excluded from being searched for -r flag')

    my_parser.add_argument('-g',
                           '--group',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Any ONE white space separated group of words to search '
                                '(this gets priority over -w parameter)')
    my_parser.add_argument('--group2',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Any TWO white space separated group of words to search '
                                '(this gets priority over -w parameter)')
    my_parser.add_argument('-w',
                           '--word',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Word to search')
    my_parser.add_argument('-W',
                           '--Word',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Optional words to search')

    my_parser.add_argument('-i',
                           '--ignore-case',
                           action='store_true',
                           help='Ignore case while searching')
    my_parser.add_argument('-n',
                           '--line-number',
                           action='store_true',
                           # TODO: Update the below statement once the search logic is finalized
                           help='Print line number (Note: printing line numbers may cause problem with -I '
                                'parameter and REGEX which use "^")')
    my_parser.add_argument('-l',
                           '--files-with-matches',
                           action='store_true',
                           help='Suppress normal output and just print the file names which satisfy the search query')
    my_parser.add_argument('-q',
                           '--quiet',
                           action='store_true',
                           help='Do not print anything for files in which no results found')
    my_parser.add_argument('-u',
                           '--url-name',
                           action='store_true',
                           help='Print clickable file names on terminal')
    my_parser.add_argument('--color',
                           metavar='WHEN',
                           action='store',
                           type=str,
                           default='auto',
                           help="Can either be auto, always or never [default: auto]")

    # NOTE: This features is being removed because it has very very less use, increases
    #       the complexity of code and reduces the efficiency of the program
    # my_parser.add_argument('-I',
    #                        '--input-record-separator',
    #                        action='store',
    #                        type=str,
    #                        help='String to separate the input based on the record separator. '
    #                             'This input will be evaluated as python string. So, to use '
    #                             'newline followed by two hyphen, just write "\\n--". '
    #                             'Note: input will be evaluated using python syntax. Hence, no need '
    #                             'to make bash correctly interpret special characters such as "\\n" or "\\t"')
    my_parser.add_argument('-O',
                           '--output-segment-separator',
                           action='store',
                           type=str,
                           default='--',
                           help='String to separate the output segments which matched the pattern [default: --]')
    my_parser.add_argument('--cmd',
                           action='append',
                           nargs='+',
                           type=str,
                           help='Command to use to read the input file and to write the output to stdout. '
                                'Insert {} in the command WITHOUT quotes to insert file name, e.g. "pdftotext {} -"')
    my_parser.add_argument('--cache',
                           action='store_true',
                           help='Cache the text content of the files read for better speed in future file reads '
                                '(text files will not be caches as there is no performance gain in that case)')

    my_parser.add_argument('--verbose',
                           action='store_true',
                           help='Print expression highlighted and number of segments which satisfied the '
                                'search conditions (Bug: content printed because of this flag will be '
                                'colored for --color=auto even if the output is not directed to a TTY)')
    my_parser.add_argument('--debug',
                           action='store_true',
                           help='Print debug information')

    # Execute the parse_args() method
    args: argparse.Namespace = my_parser.parse_args()
    print(args)
    g_fms_settings.initialize_from_argparse_namespace(args)
    g_fms_settings.initialize_data()


def exit_handler():
    # Try Except is used to handle the case where "colorama" is not installed
    global g_logger
    g_logger.info('exit_handler called')
    try:
        colorama.deinit()
    except:
        pass


atexit.register(exit_handler)
# noinspection PyRedeclaration
g_logger = logging.getLogger(__name__)
# noinspection PyRedeclaration
g_fms_settings = FmsSettings()

if __name__ == '__main__':
    my_main()
