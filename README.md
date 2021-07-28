# Context-Search-fms
grep like utility to search text, docx and PDF files for context and highlight using different colors


### Why use `fms` ?

Has it ever happened that you know a few words of a line/paragraph but do not know in which document or in which page of the document you had read it ? If yes, then use `fms`. It will help you find the line/paragraph/document in a jiffy using Extended Regular Expression ([Regexp Syntax Summary](https://www.greenend.org.uk/rjk/tech/regexp.html))


### Installation Steps and Requirements to use `fms`

- https://github.com/alttch/neotermcolor/
    ```bash
    pip install neotermcolor
    ```

- https://github.com/mbornet-hl/hl
    - Its binary can be downloaded from [https://github.com/mbornet-hl/hl/raw/master/hl](https://github.com/mbornet-hl/hl/raw/master/hl)
        ```bash
        wget https://github.com/mbornet-hl/hl/raw/master/hl
        ```
    - Add its location to `PATH`
        ```bash
        PATH="$PATH:path_to_hl"
        ```

- Download `fms.py` and add it to `PATH`
    ```bash
    wget https://github.com/fenilgmehta/Context-Search-fms/raw/main/fms.py
    PATH="$PATH:path_to_fms"
    ```

- Enjoy :)
    ```bash
    fms.py --help
    ```


### Example
- `fms -in -C 3 -p FmsStory.md -I '\n\n\n' -O'---------' -g 'why fms'`
  ![Sample 1](./imgs/sample_01.png)
- `fms -in -C 3 -p FmsStory.md -I '\n\n\n' -O'---------' -w 'multi(-)?word' -w 'search'`
  ![Sample 2](./imgs/sample_02.png)


### Usage

```bash
# Print the version of FMS you are using
fms.py --version

# Print help
fms.py --help

```

```
usage: fms.py [-h] [--version]
              [-p PATH [PATH ...]] [-P PATHS [PATHS ...]] [-r [RECURSIVE]] [-x EXTENSIONS [EXTENSIONS ...]]
              [-i] [-l] [-C --context]
              [-g --group] [-w --word [--word ...]] [-W --Word [--Word ...]]
              [--color COLOR] [-n] [-v] [-Q]
              [-I INPUT_RECORD_SEPARATOR] [-O OUTPUT_SEGMENT_SEPARATOR]
              [--cmd CMD]
              [-D]

Smart multi-word context search across multiples lines

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -p PATH [PATH ...], --path PATH [PATH ...]
                        The path to the text file to search
  -P PATHS [PATHS ...], --Paths PATHS [PATHS ...]
                        The list of paths to the text files to search
  -r [RECURSIVE], --recursive [RECURSIVE]
                        The list of paths to be used for recursive search
                        [default: .]
  -x EXTENSIONS [EXTENSIONS ...], --extensions EXTENSIONS [EXTENSIONS ...]
                        Files with these extensions only to be searched for -r
                        flag (Example Usage: -x md -x pdf OR -x "md pdf")
                        (Note: for "file.tar.gz" only "-x gz" should be used)
  -i, --ignore-case     Ignore case while searching
  -l, --files-with-matches
                        Supress normal output and just print the file names
                        which satisfy the search query
  -C --context          Number of lines in the context [default: 10]
  -g --group            Any white space separated group of words to search
                        (this gets priority over -w parameter)
  -w --word [--word ...]
                        Word to search
  -W --Word [--Word ...]
                        Optional words to search
  --color COLOR         Can either be auto, always or never [default: auto]
  -n, --line-number     Print line number (Note: printing line numbers may
                        cause problem -I parameter and REGEX which use "^")
  -v, --verbose         Print expression highlighted and number of segments
                        which satisfied the search conditions (Bug: content
                        printed because of this flag will be colored for
                        --color=auto even if the output is not directed to a
                        TTY)
  -Q                    Do not print anything for files in which no results
                        found
  -I INPUT_RECORD_SEPARATOR, --input-record-separator INPUT_RECORD_SEPARATOR
                        String to separate the input based on the record
                        separator. This input will be evaluated as python
                        string. So, to use newline followed by two hyphen,
                        just write "\n--". Note: input will be evaluated using
                        python syntax. Hence, no need to make bash correctly
                        interpret special characters such as "\n" or "\t"
  -O OUTPUT_SEGMENT_SEPARATOR, --output-segment-separator OUTPUT_SEGMENT_SEPARATOR
                        String to separate the output segments which matched
                        the pattern
  --cmd CMD             Command to use to read the input file and to write the
                        output to stdout. Insert {} in the command WITHOUT
                        quotes to insert file name, e.g. "pdftotext {} -"
  -D, --debug           Print debug information

Enjoy the program :)
```

