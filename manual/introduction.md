---
title: Webify
description: A python utility for generating static websites and course notes. 
more: >
             Webify uses pandoc to convert markdown documents in html
             webpages, LaTeX articles, and beamer slides.
             Webify is designed primarily to create course content for
             math-oriented or programming heaving courses, since it supports
             both code syntax-hilighting and LaTeX mathematical notation.
             It supports both Jinja2 and Mustache templating engine that can
             process data stored in yaml files and yaml front matter within
             markdown files to create beautiful documents and websites.
render: "{{__root__}}/_templates/main_template.html"
web: "https://github.com/faisalqureshi/webify"
preprocess-buffer: False
html-img: "{{__root__}}/_templates/img.mustache"
copy-source: True

---

First, some history.  Back in 2017 I was getting increasingly frustrated with using Microsoft PowerPoint and Apple Keynote for creating my course slides.  While both are excellent presentation softwares, with extensive multimedia capabilities, neither supported including 1) code listings with automatic syntax highlighting and 2) LaTeX mathematical notations.  I was able to get around these shortcomings by relying upon custom scripts and third-party tools, such as LaTeXIt.  It was tedious, and I was searching for a tool that would allow me to create static course content for programming and math-oriented courses.

I was aware of the LaTeX ecosystem for creating technical documentation.  I have been using LaTeX for many years, and my graduate students have used Beamer before for creating presentations.  LaTeX and Beamer looked promising for creating course content for my courses.  As I was pondering moving over to the LaTeX ecosystem for creating course content, I stumbled upon markdown and pandoc. 

- [Markdown](http://johnmacfarlane.net) is a lightweight text markup language, which can be used to specify simple formatting instructions.  A number of markdown extensions also support mathematical notations using LaTeX and code blocks.  

- [Pandoc](https://pandoc.org/index.html) is a document conversion utility written by [John MacFarlane](http://johnmacfarlane.net).  Pandoc supports conversion from/to a document written in markdown to other popular formats, including html, LaTeX, beamer slides, Microsoft Word, etc.  Most importantly for me, pandoc can convert markdown documents to HTML and PDF.  Pandoc uses a number of typesetting engines, including pdflatex, xelatex, and lualatex, to convert markdown documents into PDF, and pandoc is able to create both LaTeX-type articles and beamer-style presentations from markdown documents.  In addition, pandoc supports markdown code-listing and LaTeX mathematical notation extensions.

I decided to go with markdown+pandoc combination.  *From henceforth I shall develop my course content in markdown, and I would use pandoc to convert my notes into the desired format (html, LaTeX articles, or a beamer slides)*.  This combination, I felt, met my requirement of using plain text to create course content.

# Installation instructions

Go <a href="#installation">here</a> or check [https://github.com/faisalqureshi/webify](https://github.com/faisalqureshi/webify).

# Webify Python Utility

This led me to develop `webify`.  A python utility to create blog aware, static websites from plaintext.  Webify "duplicates" each file found in the source directory at the destination directory according to the following three rules:

- A markdown file is converted to the desired format using pandoc utility.  Currently, webify supports markdown-to-html, markdown-to-LaTeX-article (pdf), and beamer-slideshow (pdf) conversions.  When markdown file is converted to html, the process also allows for the possibility of consuming markdown contents within a [mustache](https://mustache.github.io) or [jinja](https://jinja.palletsprojects.com/en/2.11.x/) template.

- An html file is processed through mustache or jinja templating engine.

- All other files are copied as is.

Information stored in yaml files is available as the rendering context (for mustache or jinja renderers).  The rendering context for each markdown file is constructed using information found in:

- [A] Yaml files in ancestor folders (up to the root directory); and
- [C] Yaml files in the current folder; and
- [F] Yaml front matter found in the current file.

In case of key collisions, the following preference ordering is used: A < C < F.  The following figure illustrates how rendering context is constructed for each file.

![Figure 1: Rendering context construction for markdown and HTML files](rc.png)

Webify is similar to [Jekyll](https://jekyllrb.com) in many respects.  However, there is a key difference.  Webify supports plaintext to LaTeX articles and Beamer slideshow conversion.  I did not find a straightforward way to accomplish this when I played around with Jekyll.  

## The rendering context

Consider the following scenario.

```
example1
├── a
│   ├── a.md
│   └── a.yaml
└── main.yaml
```

The rendering context for file `a.md` will include information from both `main.yaml` and `a.yaml` files, in addition to the information stored in its yaml front matter.  Say the contents of `main.yaml` are:

```
---
title: Webify test site
name: Winnie
```

and the contents of `a.yaml` file are:

```
---
name: Tigger
author: Bugs bunny
keyword: tigger
```

and the contents of `a.md` file are:

```
---
keyword: stuff
---
Important stuff.
```

then the rendering context for `a.md` will be:

```
title: Webify test site
name: Tigger
author: Bugs bunny
keyword: stuff
```

### Global rendering context

Webify adds the following entries to the top-level rendering context.

```yaml
__root__: <source directory>
__version__: <version information>
__last_updated__: yyyy-MM-dd hh:mm
```

`__root__` key contains relative path to the root folder always.

### Mustache vs Jinja Rendering

Jinja is a full-featured templating engine for Python.  Mustache on the other hand is a logic-less templating engine.  Mustache is much easier to use; however, it cannot really be used in complicated settings that require some sort of logic to be executed.  

The most important thing to keep in mind is that while mustache can deal with keys with dashes (`-`); where as, jinja cannot.  If you want to use keys in a jinja template, use underscore instead (`_`).

For example:

```txt
object-id: 9
```

can be used in a mustache template using `{{object-id}}`; however, it cannot be used within a jinja template.  Use instead

```txt
object_id: 9
```

which can be used in jinja template using `{{object_id}}`.

Aside: you'll notice that both webify and mdfile use dashes (`-`) for certain keys internally.  This is intentional.  I find dashes (`-`) to be more readable.  Internal keys that are available to be used during rendering start with a double underscore `__`.

## The `_partials` folder

Each time webify processes a folder, it first looks whether or not the folder contains a sub-folder, called `_partials`.  If a `_partials` sub-folder is found, then items within this folder are processed.  Items within the `_partials` sub-folder are added to the rendering context for its parent folder.  This allows a mechanism to create common web-snippets, such as headers, footers, and navigation items, that can be used in any file that is stored in this (the parent of `_partials`) folder or one of its sub-folders.

Consider the following situation.

```
example2
├── _partials
│   ├── footer.html
│   ├── header.html
│   ├── nav.md
│   └── nav.yaml
└── index.md
```

Here, the rendering context for `index.md` file includes the entries, `footer_html`, `header_html`, and `nav_md`.  Each of these entries correspond to the processed `footer.html`, `header.html`, and `nav.md` file contents.

### `.webifyignore` for ignoring files and folders

File `.webifyignore` serves a similar purpose to `.gitignore`.  Files or folder added to `.webifyignore` file are ignored by webify utility.  An example `.webifyignore` is provided below.

```
_templates
*~
.*
.git
.gitignore
.DS_Store
\#*
.pynb_checkpoints
```

## Copying source markdown files to the destination

Webify's default behaviour is to process markdown files to create 1) LaTeX articles, 2) beamer slides, or 3) html pages.  This means that webify does not copy the source markdown file to the destination.  E.g., a markdown files `example.md` will be appear as either `example.pdf` (cases 1 and 2) or `example.html` (case 3) at the destination location.  Sometimes however it is desirable to copy the source markdown file to the destination location.  This can be achieved by using the `copy-source` flag in the yaml front matter as follows.

```txt
---
copy-source: True

---
File contents ...
```

The [markdown source](lorem-html.md) for this [html](lorem-html.html) file was copied using this mechanism.  Without this flag, `lorem-html.md` will not be available in the destination folder.

## Ignoring files

It is possible to ignore files the current folder by including this information in a yaml file as follows:

```yaml
---
ignore:
  - file: file1.md
    ignore: True
  - file: file2.md
    ignore: False
```

_Aside_: The same effect can be achieved by adding this file to the `.webifyignore` file.

### Ignoring markdown files

Use to `ignore` key to force webify to ignore a markdown file during website generation.

```txt
---
ignore: True

---
File contents ...
```

Webify will not process the above file.  The default value for `ignore` is `False`.

## Time depended availability

It is possible to specify availability, i.e., start time and end time, for any file in the "current folder" by including this information in a yaml file as follows

```yaml
---
availability:
  - file: file1.md
    start: 22 June
    end: 23 June 6 pm
  - file: file2.html
    start: 4 June 12 pm
  - file: file3.png
    end: 31 May 2035 11:59 pm
```

Note that availability information is folder specific, and it only applies to files present in that folder.  Files for which no availability information is specified are always available.  In the above example, `file1.md` will only be available between 12 am, June 22 and 6 pm June 23.  `file2.html` will be available after 12 pm June 4.  Similarly `file3.png` will be available before 11:59 pm May 31, 2020.

Note also that if you are not running webify in the background (check out the `--live` option), you will have to periodically run it for any changes to take effect.

In addition also note that webify currently doesn't support timezone aware time processing.

### Time dependent processing for markdown files

Use `availability` key in the front matter to enable time dependent processing.  

```md
---
availability:
  start: 22 Jan 2020 10 am
  end: 22 Jan 2020 11:30 am

---
File contents ...
```

Folder level availability overrides file level availability information.  

## YAML front matter: pandoc filtering

It is possible to apply text filters to data loaded from yaml files.  One common filter is pandoc, which uses pandoc utility to convert markdown text to html text.  This yaml file

```
item1: "_pandoc_ This is [cbc](http://www.cbc.ca)."
item2: "This is [bbc](http://www.bbc.co.uk)."
```

constructs the following rendering context

```
item1: "This is <a href="http://www.cbc.ca">cbc</a>."
item2: "This is [bbc](http://www.bbc.co.uk)."
```

The `_pandoc_` tag is used to invoke pandoc filter on a particular data item.

## YAML front matter: mustache preprocessing

It is possible to process yaml front matter via mustache renderer before adding it to the rendering context for the current file.  The rendering context when processing front matter is constructed from information stored in yaml files present in the current folder and in ancestor folders (up to the root folder).

Consider the following file.

```
---
template: {{__root__}}/_templates/web.html

---
This is a markdown file.
```

If rendering context contains the following:

```
__root__: /Users/foo/web
```

Then after mustache pre-processing this file would become:

```
---
template: /Users/foo/web/_templates/web.html

---
This is a markdown file.
```

A typical use of mustache preprocessing is to specify site-wide template or render files.  This can be achieved by specifying the paths of these files with respect to the root folder of the site. 

Use the `preprocess-frontmatter` to control this behaviour.  The default value for this key is `True`.

## Markdown file contents: mustache preprocessing

During markdown-to-html conversion, it is also possible to preprocess buffer contents using mustache.  Consider file `letter.md` below:

```txt
Dear {{name}}:

Please check out webify [here](https://github.com/faisalqureshi/webify).

Regards.
```

If the rendering context contains 

```txt
name: Marie
```

then the file contents will become

```txt
Dear Marie:

Please check out webify [here](https://github.com/faisalqureshi/webify).

Regards.
```

The preprocessed contents can be passed to pandoc for conversion to html.

Use the `preprocess-buffer` to control this behavior.  The default value for this key for markdown-to-html conversion is `True`.

## Blogging

Webify version > 3.1 supports blogging by adding the following special keys to the rendering context.  Each key contains file lists that can be used within a jinja template to construct a blog index page.  

- `__md__`: list of markdown files found in the current folder (both raw markdown files and their corresponding rendered files)
- `__html__`: list of html files found in the current folder
- `__ipynb__`: list of Jupyter Notebook files (both ipynb files and their corresponding rendered html files)
- `__misc__`: list of all other files found in the current folder
- `__files__`: list of all files found in the current folder and all its descendent trees.  Note that yaml files are not included in this list.  Yaml files are used for configuration only, and these files are not copied over to the destination.

Each file object in these lists contains the following keys:

- `src_filename`
- `filename`
- `is_available`
- `is_ignored`
- `filepath`
- `output_filepath`
- `file_type`
- `obj`
- `data`
- `ext`

The relevant keys for constructing a blog index are: `filename` and `is_available`.  `data` key allows one to look into the yaml front matter for any markdown file.  This field can be used to get information about the markdown file, such as title, author, date, etc. Key `file_type` is used internally to disinguish processing steps for the supported filetypes.  Use `ext` key to identify the type of the file.  This key contains file extension. 

Any html or markdown file can use these lists to construct blog index pages.  A special key `__me__` identifies this markdown or html file.  The following jinja snippet, for example, constructs a simple blog index.

```jinja
{% for post in __md__ %}
    {% if (post.is_available and __me__ != post.filename and post.ext != ".md" ) %}
    <li><a href="{{ post.filename }}">{{ post.filename }}</a></li>
    {% endif %}
{% endfor %}
```

## A note about Juputer Notebooks

Webify provides three ways of treating a Jupyter Notebook:

1. Render the Jupyter Notebook as an HTML file and copy to the desitination folder;
2. Copy the Jupyter Notebook as is to the destination folder; and
3. Render the Jupyter Notebook as an HTML and copy both the HTML and the original file to the destination folder.

Option 1 is useful when creating non-editable notes from Jupyter Notebooks.  This is the default behavior, which can be overwritten by adding the following in a yaml file.  

~~~
jupyternotebooks:
  render-html: False | *True
  copy-source: *False | True
~~~

This information is added to the rendering context of the current folder and its sub-folder and all Jupyter Notebooks sitting in this folder or its sub-folders will be processed according to these instructions.

## Live view

It is possible to run webify in the background.  This combined with `<meta http-equiv="refresh" content="5">` in the header of the generated html files creates a live view environment that is easy to use.  Check out the `--live` switch.

```bash
webify.bat --live src-folder destination-folder
```

## MDFile Python Utility

Webify uses mdfile python utility to convert markdown files to the desired output format: html pages, LaTeX articles, or beamer slides.  MDfile is built around pandoc and uses pypandoc package to perform markdown conversion.  For markdown-to-HTML conversion, mdfile utility supports mustache and jinja rendering.  Specifically, HTML contents from the pandoc conversion step are processed via mustache or jinja templating engine.  Mustache and jinja rendering has access to this file's rendering context (see Figure 1).

### Markdown to LaTeX articles or Beamer slides

The following figure provides an overview of markdown to LaTeX article or Beamer slides conversion.

![Figure 2: Markdown to PDF](md-to-pdf.png)

The following *keys* are supported during markdown to LaTeX or Beamer slides conversion.  These *keys* controls how pandoc is used to convert the markdown file.

#### YAML front matter

```yaml
to: *html | pdf | beamer
pdf-engine:              lualatex | *pdflatex
preprocess-frontmatter:  *True | False
preprocess-buffer:       False
create-output-file:      True
ignore:                  True | *False
template:                *None | <pandoc-template>
highlight-style:         kate | *pygments
slide-level:             *1 | 2
include-in-header:       *None | <filename(s)>
include-before-body:     *None | <filename(s)>
include-after-body:      *None | <filename(s)>
bib:                     *None | <bibtex files(s)>
csl:                     *None | <csl file>
availability:
  start:                 *bigbang | Date and Time
  end:                   *ragnarok | Date and Time
```

- `*` next to a value indicates the default value.
- Need to specify either `pdf` or `beamer` for the `to` key.
- If `template` is not provided, default pandoc template is used.   Use `pandoc -D *FORMAT*` to see the default template.
- `slide-level` is only available when converting markdown to beamer slide.
- If `pdf-engine` isn't specified, pandoc uses the default LaTeX distribution.
- `create-output-file` must be `True`.
- `preprocess-buffer` must be `False`.
- Yaml front matter is only preprocessed via mustache if `preprocess-frontmatter` is `True`.
- `include-in-header`, `include-before-body`, and `include-after-body` can be used to specify files whose contents will be inserted as the name suggests: in the header (before `\begin{document}`), in the body (after `\begin{document}` but before everything else), and just before `\end{document}`.  In each case, multiple files can be specified.
- `bib`: specifies the bibliography file(s).
- `csl`: specifies a [Citation Style Language](https://citationstyles.org) file that control how citations are processed.
- `availability`: this key is only used by webify.

#### Example

- [LaTeX article](lorem-article.pdf) ([Source](lorem-article.md))
- [Beamer slides](lorem-slides.pdf) ([Source](lorem-slides.md))

### Markdown to HTML

The following figure provides an overview of markdown to HTML conversion.

![Figure 2: Markdown to HTML](md-to-html.png)

#### YAML front matter

```yaml
to: *html | pdf | beamer
preprocess-frontmatter:  *True | False
preprocess-buffer:       *True | False
standalone-html:         True  | *False
ignore:                  True | *False
template:                *None | <pandoc-template>
highlight-style:         kate | *pygments
include-in-header:       *None | <filename(s)>
include-before-body:     *None | <filename(s)>
include-after-body:      *None | <filename(s)>
css:                     *None | <CSS file(s)>
html-img:                *None | <filename>
html-imgs:               *None | <filename>
html-vid:                *None | <filename>
html-vids:               *None | <filename>
availability:
  start:                 *bigbang | Date and Time
  end:                   *ragnarok | Date and Time
```

- `*` next to a value indicates the default value.
- `to` key must be `html`
- If `standalone-html` is true then pandoc is used to generate html using its default markdown-to-html template or the template specified by `template` key.
- If `template` is not provided, default pandoc template is used.   Use `pandoc -D html5` to see the default template.
- Yaml front matter is only preprocessed via mustache if `preprocess-frontmatter` is `True`.
- Media filters tags `html-img`, `html-imgs`, `html-vid` and `html-vids` specify mustache templates to override the default conversion of markdown media tag `![Caption](Image or Video file)`.  See below for more details.  Supported file extensions are `mp4`, `png`, `jpeg`, `gif` and `jpg`.
- File contents can be preprocessed via mustache if `preprocess-buffer` is `True`.  This is done before the contents are sent to pandoc for conversion.
- `include-in-header`, `include-before-body`, and `include-after-body` can be used to specify files whose contents will be inserted as the name suggests: in the header (between `<head>` and `</head>`), in the body (after `<body>` tag but before everything else), and just after `</body>`.  In each case, multiple files can be specified.
- `css`: specifies the CSS file(s).
- `availability`: this key is only used by webify.

The following YAML frontmatter keys are used when mdfile is used within webify.

```yaml
render:                  *None | <render file>
renderer:                *Jinja | Mustache
create-output-file:      *True | False
```

- If `create-output-file` is `False`, markdown contents are saved to a buffer.  This functionality is used in `webify` during `_partials` folder processing. 
- `render` specifies the mustache or jinja template.  The html contents generated using pandoc are passed to this template as the `body` key.  This page, for example, uses this mechanism.  Contents of the YAML frontmatter for each markdown file are also available.  Check source <a href="introduction.md">here</a>.  Render file is <a href="_templates/main_template.html">here</a>.
- Key `renderer` specifies whether mustache or jinja template is used.


#### Example

- [Generated HTML](lorem-html.html) ([Source](lorem-html.md))

#### Media filters

Markdown supports adding an image (or possibly a video) file to the document via the following syntax:

```txt
![Caption](Media file)
```

It is often desirable to control how media is displayed.  Use `html-img`, `html-imgs`, `html-vid` and `html-vids` tags to specify mustache templates that will replace the `![Caption](Media file)` with html code before further processing via mustache or pandoc.  Check out `webify/mdfilter` folder for example templates.

MDfile utility will consume the `![Caption](Media file)` and constructs the following rendering context that will be available for the mustache template that will replace this string with HTML code.

```txt
file: Media file
type: image | video
caption: Caption
```

The type of the media file (image or video) will determine which template (`html-img` or `html-vid`) will be used.

It is also possible to use the above syntax that works for a single file to multiple files as follows:

```txt
![Caption](Media file 1 | Media file 2 | ... | Media file N)
```

In this case the rendering context is:

```txt
files: 
  - file: Media file 1
  - file: Media file 2
  ...
  - file: Media file N
caption: Caption
```

The type of the media files (images or videos) will determine which template (`html-imgs` or `html-vids`) will be used.

##### Example media filters

**img.mustache**

```txt
<div class="row">
  <div class="col-lg-12">
    <figure class="figure">
      <a href="{{file}}"><img class="img-responsive" width="100%" src="{{file}}" alt="{{caption}}"></a>
     {{#caption}}<figcaption class="figure-caption">{{caption}}</figcaption>{{/caption}}
    </figure>
  </div>
</div>
```

**vid.mustache**

```html
<div class="embed-responsive embed-responsive-16by9">
<iframe class="embed-responsive-item" src="{{file}}"></iframe>
</div>
```

##### Embedding context info in Caption

It is possible to embed extra context info in captions as follows

```txt
![Caption !{'a':'x', 'b':'y'}](Media File)
```

In this case the (rendering) context available to media filters will also include 'a':'x' and 'b':'z' in addition to 
the usual entries (`caption`,`file`).  The following media filter, e.g., uses width information.

**Definition**

```txt
![Caption !{'width':'12%'}](Media file)
```

**Filter**

```html
<div class="row">
<div class="col-lg-12 text-center">
<figure class="figure">
<a href="{{file}}"><img class="img-fluid" src="{{file}}" alt="{{caption}}" {{#width}}width="{{width}}"{{/width}}></a>
{{#caption}}<figcaption class="figure-caption">{{caption}}</figcaption>{{/caption}}
</figure>
</div>
</div>
```

<h1 id="installation"> Installation and Usage</h1>

## Mac OSX

1. Install [MacTeX](https://www.tug.org/mactex/)
2. Install [Pandoc](https://pandoc.org/installing.html)
3. Optionally install pandoc's cite-proc citation parser
4. Get [Webify](https://github.com/faisalqureshi/webify)
5. Setup Python.  The current version of webify uses Python > 3.0.  Run `pip -r install webify/webify/requirements.txt` to set up Python.  Optionally you can use `venv` to create a standalone webify Python environment.  See [here](https://docs.python.org/3/library/venv.html) for more details.
6. Add webify/webify directory to PATH environment variable.  This folder contains two scripts `mdfile` and `webify`.  Use these scripts to run the utilities.
7. Set environment variables `WEBIFY_DIR` and `WEBIFY_PYTHON`.

## Windows

1. Install [MicTeX](https://miktex.org/)
2. Install [Pandoc](https://pandoc.org/installing.html)
3. Optionally install pandoc's cite-proc citation parser
4. Get [Webify](https://github.com/faisalqureshi/webify)
5. Setup Python.  The current version of webify uses Python > 3.0.  Run `pip -r install webify/webify/requirements.txt` to set up Python.  *Use your preferred method for setting up windows python environment.  We also have had some success with using docker containers.*
6. Add webify/webify directory to PATH environment variable.  This folder contains two scripts `mdfile.bat` and `webify.bat`.  Use these scripts to run the utilities.
7. Set environment variables `WEBIFY_DIR` and `WEBIFY_PYTHON`.

**Live Mode is not available in windows.**

### Windows Subsystem Linux

One way to enable live mode (untested) is to use WSL.  In order to do so, please also install the [Xming XServer for Windows](https://sourceforge.net/projects/xming/).  There is an issue with Keyboard Listener that tries to connect to `DISPLAY:0`.

### Unixify Windows

Another option is to use the excellent [Msys2](https://www.msys2.org/) for windows.  It comes with `pacman` package manager.  It will provide you a unix-like experience in windows.  It is better integrated with windows, e.g., it is able to access Google Drive, which WSL cannot access.  Why doesn't google support linux for Google Drive is beyond me.  You may also look at the newly released [Windows Terminal](https://www.microsoft.com/en-ca/p/windows-terminal/9n0dx20hk701?activetab=pivot:overviewtab) for a better terminal experience than the good old dos terminal.  Who uses it any ways.  OpenSSH  in Msys2 doesn't recognize `c:\Users\$USERNAME` directory.  Your best best is to copy `.ssh` folder `/c/mysys64/home/$USERNAME`.  This will allow you to use `rsync` with `ssh` to upload the generated content on to a remote server. 

## Linux

1. `sudo apt-get install texlive-full`
2. `sudo apt-get install pandoc`
3. Get [Webify](https://github.com/faisalqureshi/webify)
4. Setup Python.  The current version of webify uses Python > 3.0.  Run `pip -r install webify/webify/requirements.txt` to set up Python.  Optionally you can use `venv` to create a standalone webify Python environment.  See [here](https://docs.python.org/3/library/venv.html) for more details.
5. Add webify/webify directory to PATH environment variable.  This folder contains two scripts `mdfile` and `webify`.  Use these scripts to run the utilities.
7. Set environment variables `WEBIFY_DIR` and `WEBIFY_PYTHON`.

## Webify Usage

Use the following command to construct a website from webify source:

```txt
webify src-folder dest-folder
```

The following commandline options, which are available for *webify*, are particularly useful for printing diagnostic information during execution.

- `--show-availability`: list files that were not processed due to time availability constraints
- `--show-not-compiled`: list markdown files that were not compiled because destination file already exists 
- `--show-compiled`: list markdown files that were compiled
- `--show-not-copied`: list files that were not copied to the destination, because destination file already exists
- `--show-ignored`: list markdown files that were not processed due to their ignore flag

By default webify only shows *warnings* or *errors*.  Use `--verbose` flag to turn on messaging; however, I find this to be not very useful when dealing with a large set of files.  There is such a thing as too much information.

Use `--help` to list the available commandline options.

### Live Mode

Use `--live` option to enable live viewing during editing.

```txt
webify --live --live-url-prefix="http://localhost/webify-manual" --upload-script=upload.sh src-folder dest-folder
```
In this mode, webify runs in the background and processes source folder into destination folder as needed.  This processing happens when:

- a file is created, deleted, or modified; and
- time availability for a file is changed.

Use `--upload-script` to specify a shell script that can be used to upload compiled website to a hosting server.

In live mode, enter `h` to see the list of available commands.

```txt
- 'h': print this message
- 'q': quit
- 'r': run webify
- 'c': webify (force file copying)
- 'i': webify (force compilation)
- 'a': webify (force compilation and file copying)
- 'w': enter url to watch (useful for live updates)
- 'b': toggle browser refresh
- 'u': run upload shell script
```

## MDfile Usage

```txt
mdfile lorem-html.md
```

Use `--help` to list available commandline options.

# Questions and Comments

Please contact Faisal Qureshi at <a href="mailto:faisal.qureshi@ontariotechu.ca">faisal.qureshi@ontariotechu.ca</a>. 

# Copyright

Faisal Qureshi    
Professor  
Computer Science     
Faculty of Science     
Ontario Tech University     
Oshawa ON L1C OG5     
Web: http://faculty.uoit.ca/qureshi    



