# Changelog

- __Terminology Used__
  - Query - list of regex/word
  - Query-Word/Word - individual regex/word
  - Segment (output) - a bunch of lines which satify the Query
  - Record (input) - a bunch of lines which are to be searched for Segments.
    - One File can have multiple Records
    - One Record can have multiple Segments

### v3.1 ()
- ADD support for __`xlsx`__, __`ods`__
- ADD -u/--url-name parameter to print clickable links for file names
- ADD exception handling to handle cases where the output pipe is closed before the writing is complete in the `highlight_words` function
- UPDATE -r/--recursive to accept file paths as well
- UPDATE default extension Exclude list
- UPDATE default -C/--context value from 10 to 7
- FIX handling of local file paths given/passed as URL
- FIX file reading using `cat` to work with files containing non-printing characters
- FIX file extension matching to work as case-insensitive
  - Used to decide how to read a file
  - Used to decide which files to include and exclude

### v3.0 (28 August 2021) 
- ADD support for __`doc`__, __`odt`__, __`epub`__, __`docm`__, __`dotx`__, __`fodt`__, __`ott`__ and __`rtf`__ files

### v2.5 (27 August 2021)
- ADD support for __`pptx`__ files
- UPDATE static typing
- UPDATE input record separator regex for the case when `\n` character is not present in the user input for `-I/--input-record-separator`

### v2.4 (23 August 2021)
- ADD __`-g2`__ and REVERT `-g` to its original working
- UPDATE default extension exclude list
- UPDATE logging format
- UPDATE `-r` in argparse to accept multiple directories in just one `-r`
  - Example: `fms -r 'dir1' 'dir2' dir3' -g 'anything_here'`
- FIX bug in working of `--color`

### v2.3 (18 August 2021)
- ADD __`-X/--extexclude`__ to allow the user to exclude files from `-r/--recursive` search whose extension is present in the exclude list
<!--  -->
- UPDATE README.md
  - Add examples
  - Update installation steps
  - Update docs
<!--  -->
- ADD exception handling for `smart_search` function
- UPDATE `-g/--group` to use two spaces as separator for Query-Words
- FIX reading of files which have single quotes in their path
- REMOVE `-P/--Paths` as all its functionality is supported by `-p/--path`

### v2.2 (28 July 2021)
- ADD example images
- ADD `FmsStory.md`
- Prevent duplicate files/paths during search
- FIX bugs in handling of command line input for `-p`, `-g`, `-w`, `-W`, `-x`
- FIX highlighting of queries ([code line](https://github.com/fenilgmehta/Context-Search-fms/commit/594bca50c5840e7fa043b5cc5ac93b8a1e54efe9#diff-9662fc5dc512ac5872e7e927ab81a67feb8dfc3a73b8e82da653a9e5eeb2faf6R214), [refer](https://github.com/mbornet-hl/hl/issues/20))

### v2.1 (28 July 2021)
- ADD support for __`docx`__ files
- UPDATE comments/documentation
- UPDATE `-r/--recursive` to use current working directory if no parameters are passed to it

### v2.0 (1 July 2021)
- __Major Release__ with lots of changes
<!--  -->
- ADD 15 new colors for highlighting Query-Words
- ADD `-q/--quiet` option to highlight Query-Word if present. However, it is not necessary for it to be present in the Segment
- ADD support for passing multiple files using `-p/--path`
- UPDATE `-g/--group` to allow multiple Queries to be passed at the same time
- FIX word highlighting
<!--  -->
- ADD `-n/--line-number` parameter to print line number
- FIX line number highlighting regex
  - `\n\d+ ` ---> `\n[0-9]+: `
  - `^\d+: ` ---> `^[0-9]+: `
<!--  -->
- ADD `-P/--Paths` parameter to specify file path which accepts globs as well
- ADD `-Q` parameter to avoid printing anything for files which do not satisfy the whole Query
- ADD garbage collection in `smart_search` and `highlight_words` function
- FIX docs
<!--  -->
- UPDATE `highlight_words` function to use [`hl`](https://github.com/mbornet-hl/hl) utility for highlighting instead of `termcolor` python library
  - Because, `hl` gives better performance and consumes less memory
  - Using `hl` instead of normal Python code avoids program crash while highlighting a segment which matched the below command:
    - `fms -i -C 20 -P test.pdf -w "valve" -g "a b c d e f g h i j k l m n o p q r s t u v w x y z"`
      - Python code would execute for 20+ seconds, use 10+ GB of RAM and then crash
      - Using `hl`, the program finishes the execution in less than 8 seconds and the memory usage of the program does not exceed 8 MB
<!--  -->
- UPDATE `read_file` function
  - ADD verbose error logging
  - UPDATE input record splitting
- CHANGE `-q` to `-W`
- FIX highlighting command
- CHANGE `-R` to `-I` (i.e. `--input-record-separator`)
- CHANGE `--group-separator` to `-O/--output-segment-separator`
- UPDATE variable names to be more clear and explicit
<!--  -->
- UPDATE shebang to work with different environments of python
- ADD `-v/--verbose` parameter to print details like:
  - The Query-Words searched and colors used to highlight them
  - Number of segments which satisfied the Query
- ADD `-r/--recursive` to perform search on all files in a directory
- ADD `-x/--extensions` to help `-r` parameter to search for file with specific file extensions only
<!--  -->
- UPDATE from `termcolor` to [`neotermcolor`](https://pypi.org/project/neotermcolor/) ([GitHub](https://github.com/alttch/neotermcolor)) library because:
  - `termcolor` is outdated
  - `neotermcolor` is being updated and new features are added too
- UDPATE `--no-color` to `--color` flag (similar to `grep`)
- ADD `-l/--files-with-matches` to only print the name of the files which contained at least one Segment which satisfied the Query (similar to `grep`)
- ADD `-D` flag to enable verbose logging to debug the program faster
- FIX exit code which is being used when exiting the program
<!--  -->
- UPDATE README.md to include:
  - Why use `fms`
  - Installation steps
  - Usage
<!--  -->
- UPDATE `-x/--extensions` flag to only perform filtering on files fetched from `-r/--recursive` flag

### v1.0 (27 April 2021)
- __First release__ after lots of offline update
