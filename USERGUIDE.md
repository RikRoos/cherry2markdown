# Userguide for cherry2md

`cherry2md.py` - converter Cherrytree notes to markdown [🌳📄] -----> [⚙️] -----> [📝]

**Table of Contents**

1. [Preface](#Preface)
1. [Installation Instructions](#Installation-Instructions)
	- [1. Create a working directory](#1-Create-a-working-directory)
	- [2. Clone the repository](#2-Clone-the-repository)
	- [3. Create and activate a virtual environment](#3.-Create-and-activate-a-virtual-environment)
	- [4. Install the package](#4-Install-the-package)
	- [5. Verify installation](#5-Verify-installation)
	- [6. Run the converter](#6-Run-the-converter)
1. [Some Design Choices](#Some-Design-Choices)
	- [How XML-tags and contents are handled](#How-XML-tags-and-contents-are-handled)
	- [How `<rich_text>` attributes are handled](#How-%60%3Crich_text%3E%60-attributes-are-handled)
	- [How the filetree is generated](#How-the-filetree-is-generated)
	- [How lists are handled](#How-lists-are-handled)
	- [How line-ends are handled](#How-line-ends-are-handled)
	- [Log & Info](#Log-&-Info)
1. [Configuration](#Configuration)
	- [TOML configuration file](#TOML-configuration-file)
	- [Note on **note.title**](#Note-on-**note.title**)
	- [Command-line Arguments](#Command-line-Arguments)
    	- [Positional Arguments:](#Positional-Arguments)
    	- [Additional Options:](#Additional-Options)

---
## Preface

Conversion of 'rich text' to markdown is a not so unambiguously job.  For instance, what to do when some text was marked up with monospace font and also marked up in italic style?  The choice that I made was to prefer monospace markup over all other styles that are present; monospace text will be  converted as 'inline code' or as a 'code block' (depending on the presence of newlines in the text).  Reason is that I personally choosed many times for monospace (just press CTRL-m in Cherrytree) over a codebox, I just found that easier to do (regretting my laziness afterwards).

I have made almost 500 notes in Cherrytree and it is was surprising to see that many notes did not match the format rules I came up with.  So this converter does not deal with all possible situations and I accept to modify some markdown notes manually after the conversion.

Cherrytree exports all images as encoded BASE64 in 'png' file format. Images will  be stored together in one 'images' directory whereby each image will be suffixed with an unique number.'''

The program reads the XML-database file exported by Cherrytree and converts all the  nodes to files and directories analogous to the hierarchy within the Cherrytree database.

This tool is written in Python (version 3.12) using standard libraries only.

Take a look at the *command-line options* and the *TOML file* in the sections that follow (see also my recommendations in the **README section** on GitHub).

---

## Installation Instructions

These steps show how to install and run **cherry2md** in a clean and isolated environment. It is recommended to keep your development tools inside a dedicated directory (e.g., `~/myprojects`) and to use a Python virtual environment.

### 1. Create a working directory

Choose or create a directory for your personal projects:

```bash
mkdir ~/myprojects    # Linux/MAc
cd ~/myprojects
```

### 2. Clone the repository

```bash
git clone https://github.com/rikroos/cherry2markdown.git
cd cherry2markdown
```

### 3. Create and activate a virtual environment

Creating a virtual environment prevents conflicts with other Python tools or system packages.

```bash
python3 -m venv venv
source venv/bin/activate     # Linux/macOS
# or on Windows:
# venv\Scripts\activate
```

Upgrade `pip` (recommended):

```bash
pip install --upgrade pip
```

### 4. Install the package

Install the project in editable/development mode:

```bash
pip install -e .
```

This allows you to modify the source code while using the installed command.

### 5. Verify installation

You can now view the available command-line options:

```bash
cherry2md --help
# or (depending on your entry point):
python cherry2md.py --help
```

### 6. Run the converter

⚠️ Warning: Before running the converter on your real Cherrytree database, make sure to read the remainder of this document. Certain configuration options, export behaviors, and recommended workflows may influence the results. Performing a few test runs first is strongly advised.

To convert a Cherrytree XML database:

```bash
cherry2md <path-to-xml-file>
```

Or, if no console script is defined:

```bash
python app/cherry2md.py <path-to-xml-file>
```

Verbose mode examples:

```bash
cherry2md <path-to-xml-file> -v     # verbose
cherry2md <path-to-xml-file> -vv    # very verbose
```

---

## Some Design Choices

### How XML-tags and contents are handled

Starting at the _root_ only the tags `<node>` are selected.
Within a `<node>` tag other `<node>` tags are recursively processed.
Other tags inside a `<node>` tag that will be processed are:

| Tag            | Descriptions                                                      |
| -------------- | ----------------------------------------------------------------- |
| `<rich_text>`  | regular tags with text                                            |
| `<codebox>`    | programming code                                                  |
| `<encode_png>` | base64 encoded images but also other text- objects like PDF-files |
| `<table>`      | text in columns like a regular table                              |
| `<link>`       | links to web-sites or other resources                             |

Only Cherrytree notes **with some content** are legible to be written as markdown file; thus empty notes are silently discarded. This can be however an issue for cases where the existance of the *note-node* it  self is functioning as some form of documentation. In that case it is advised to  drop a character into the empty Cherrytree note e.g. a "!" or a "." before exporting the XML-file. 

In case an empty node is referencing one or multiple sub-nodes then these sub-nodes will be placed in a newly created directory that wil be named after the title of that parent-node; non-alphabetical chars are cleansed in that name.

---
### How `<rich_text>` attributes are handled

The tag **`<rich_text>`** has attributes that formats the text in a Cherrytree note.
These attributes has to be translated into some _arbitrary_ markdown formats. 

- **Attribute "scale" with values "h1" till "h6" :**  Exported as "#" till "######".

- **Attribute "family" with value "monospace" :** Textfragment is exported surrounded by \`\`\`.

- How superscript and subscript are handled:  markdown (as I know) does not support these out of the box. I choose to translate these to matching UTF-8 characters.

---
### How the filetree is generated

Only tags `<node>` that contain one or more tags `<rich_text>` are written to a markdown file. This markdown file is named after the name of the node; spaces are replaced with underscores.

In case a tag `<node>` contains other tags `<node>` a new directory will be created with the name of the parent node (without the ".md" extension).  But this is only done if at least one child node contains text fragment(s) which will result in a new note file for that child.

If the parent `<node>` it self also contains text fragment(s) then a new note  file is created as a sibling of the created directory that will hold the child notes of this parent `<node>`.

So, a branch in the tree of Cherrytree notes without any text are silently discarded from output (no empty note files will be generated)! See also  paragraph 1 which commented on this case.

---
### How lists are handled

Cherrytree has a few buttons to transform selected lines into lists with the desired list-item symbol. This will result in plain text in the text fragment which will be exported as is (UTF-characters). 

• item 1
• item 2
• item 3

☐ item 1
☐ item 2
☐ item 3

1. item 1
2. item 2
3. item 3

---
### How line-ends are handled

In Markdown line-ends are processed as if not existing. So lines are concatenated together. Only an empty line is respected; however, the following empty lines are then ignored. But I wanted to migrate these additional empty lines too.

A simple trick is to append 2 spaces to each line-end. This way you don't have to worry about the line-ends.

In the config directory you will find a TOML-file with a few settings that dictates how to deal with line-ends. Default 2 spaces are appended to each line found in the XML-file to mimic the layout of the orignal note layout.

---
### Log & Info

After finishing the conversion a list with some counts will be printed but  only when commandline parameter -v or -vv is used .
A note about the count of 'created directories': only created directories  containing a real markdown-note are counted for. Reason is that  directories are created with the option 'parents=True'.

When running in DRY-RUN mode, afterwards a message will be printed to warn you nothing has been created.

---
## Configuration

The converter can be customized using a TOML file (for content-related settings) and command-line parameters (for runtime behavior).

---
### TOML configuration file

**Locatie:** `app/config/cherry2md.toml`

| Key                              | Description                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| skip_notes                       | ignore Cherrytree notes with the specified IDs                                       |
| images_link                      | root path for the image location (a dedicated subdirectory in Obsidian)              |
| pdf_link                         | root path for PDF files (a dedicated subdirectory in Obsidian)                       |
| others_link                      | root path for other file types (a dedicated subdirectory in Obsidian)                |
| horizontal_rule                  | markup                                                                               |
| italic                           | markup                                                                               |
| heavy                            | markup                                                                               |
| strikethrough                    | markup                                                                               |
| background_color                 | markup                                                                               |
| superscript                      | markup                                                                               |
| subscript                        | markup                                                                               |
| missing_linklabel.max_chars      | default: `99` — maximum number of characters for auto-generated link text            |
| missing_linklabel.shortened_text | default: `"...(more)"` — text appended when a label is shortened                     |
| fmt_timestamp_created            | `"%Y-%m-%d %H:%M:%S"`                                                                |
| fmt_timestamp_exported           | `"%Y-%m-%d %H:%M:%S %z"`                                                             |
| append_each_line                 | default: two spaces, which forces a line break                                       |
| replace_empty_line_with          | default: `""` (empty), or e.g. `"\\"` or `<br>`                                      |
| note.title                       | default: disabled — optional prefix placed before the original note text             |
| note.closing                     | default: enabled — optional postfix placed after the original note (export metadata) |

---

### Note on **note.title**

Obsidian has a feature that automatically assigns each note a `# chapter title` based on the Markdown filename.  
If this is not desired and the user disables that feature, the converter can be configured to generate a title instead.

In the TOML file the prefix text is current set to only a line `---`. You can embed the variable `{title}` to display the generated title.

---
### Command-line Arguments

The converter always requires at least one argument: the path to the XML file that should be converted.

``` bash
$ python cherry2md.py <path-to-xml-file>
```

Additional options can be provided, for example to display extra information about the results:

```bash
$ python cherry2md.py <path-to-xml-file> -v
```

Or to display even more verbose output:

```bash
$ python cherry2md.py <path-to-xml-file> -vv
```

The available runtime command-line arguments can be listed with:

```bash
$ python cherry2md.py --help
```

---
#### Positional Arguments:

| argument       | descriptions                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| `xml_filepath` | the path and filename of the Cherrytree XML file to process; this can be an absolute or a relative path |

---
#### Additional Options:
  
| argument                                  | descriptions                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-h, --help`                              | Show this help message and exit.                                                                                                                                                                                                                                                                                                                                                                                         |
| `-a, --absolute_path`                     | References inside markdown notes: use absolute path instead of relative paths in references to other files like images.<br><br>Default a relative path is generated because that makes it possible to move the generated notes-tree to a other place in the filesystem afterwards. In case you like to browse your notes-tree in a sandwiched environment, for example with 'jail', you can opt in for an absolute path. |
| `-c, --clean_env`                         | Clean up the output environment: purge the directory 'markdown' from the 'data_dir' directory.<br>You will be prompted for confirmation `[y/n]`."<br><br>-> Be carefull not to run this option after having made changes manually to your newly created markdown notes!                                                                                                                                                  |
| `-d, --data_dir DATA_DIR`                 | Directory for containing the output, will be created if not existing already.<br>default: `'./data/_cherry2md_'` .<br><br>For security reasons, the data directory is always followed by a system generated directory called _ch2md_                                                                                                                                                                                         |
| `-x, --attachment_index ATTACHMENT_INDEX` | Starting number for indexing attachment files; default is 1                                                                                                                                                                                                                                                                                                                                                              |
| `-q, --quiet`                             | No output information on screen but redirect all info to file `'stdout.log'`                                                                                                                                                                                                                                                                                                                                             |
| `-u, --unique_id UNIQUE_ID`               | Convert only a specific Cherrytree-note with the Cherrytree-note unique_id (a XML-attribute)                                                                                                                                                                                                                                                                                                                                     |
| `-v, --verbosity`                         | Increase output verbosity: <br>`-v   : `this shows used directory paths and a table with counts <br>`-vv  :` this shows additionally filepaths of created notes and directories                                                                                                                                                                                                                                          |
| `-y, --dryrun`                            | fake run: disable the creation of any file on disk                                                                                                                                                                                                                                                                                                                                                                       |

---

*The Author, November 2025*
