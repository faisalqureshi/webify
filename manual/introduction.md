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

---

First, some history.  Back in 2017 I was getting increasingly frustrated with using Microsoft PowerPoint and Apple Keynote for creating my course slides.  While both are excellent presentation softwares, with extensive multimedia capabilities, neither supported including 1) code listings with automatic syntax highlighting and 2) LaTeX mathematical notations.  I was able to get around these shortcomings by relying upon custom scripts and third-party tools, such as LaTeXIt.  It was tedious, and I was searching for a tool that would allow me to create static course content for programming and math-oriented courses.

I was aware of the LaTeX ecosystem for creating technical documentation.  I have been using LaTeX for many years, and my graduate students have used Beamer before for creating presentations.  LaTeX and Beamer looked promising for creating course content for my courses.  As I was pondering moving over to the LaTeX ecosystem for creating course content, I stumbled upon markdown and pandoc. 

- Markdown is a lightweight text markup language, which can be used to specify formatting information.  A number of markdown extensions also support mathematical notations using LaTeX and code blocks.  

- [Pandoc](https://pandoc.org/index.html) is a document conversion utility developed by XXX.  Pandoc supports conversion between a wide variety of markdown languages.  Most importantly for me, pandoc can convert markdown documents to HTML and PDF.  Pandoc uses a number of typesetting engines, including pdflatex, xelatex, and lualatex, to convert markdown documents into PDF, and pandoc is able to create both LaTeX-type articles and beamer-style presentations from markdown documents.  In addition, pandoc supports markdown code-listing and LaTeX mathematical notation extensions.

I decided to go with markdown+pandoc combination.  From henceforth I would develop my course content in markdown, and I would use pandoc to convert my notes into the desired format (html, LaTeX artciles, or a beamer slide).

## MDFile Utility

MDfile utility processes single markdown files, converting these to html pages, LaTeX articles, or beamer slides using pandoc.  In case of conversion to html pages, it is able to use mustache and jinja2 renderers.  This allows mdfile utility to generate complicated html pages by using information stored in external yaml files in addition to the contents of the markdown file.  Information stored in external yaml files and the yaml front matter is available as the rendering context during the rendering process.  

### Background

My course notes are often spread over multiple markdown files.  I needed a way to automate markdown-to-desired-output conversion.  One straightforward option was to use a bash script to automate this conversion.  I found this approach to be limiting.  There wasn't an easy way to treat various files differently.  Say I wanted to convert `a.md` to a beamer slideshow and `b.md` to an html page?  I couldn't find a way to write a bash script that would do this for me.  I knew that markdown files support metadata through a yaml header.  This suggests that we can include file specific processing instructions in the markdown file itself.  At processing time, we can use these instructons to process the markdown file accordingly.  MDfile is Python utility built around pandoc.  It uses pandoc to do all the heavy lifting, i.e., actual document conversion.  However, it loads in the yaml metadata from the markdown file and uses this information to set up pandoc conversion appropriately.  Yaml front matter can also be used to speciify custom options for pandoc conversions.  MDfile relies upon pandoc Python bindings.  Specifically, MDFile supports 1) markdown-to-html, 2) markdown-to-LaTeX-article, and 3) markdown-to-beamer-slides conversions.

Consider the three files:

- `lorem-article.md` ([generated LaTeX article](lorem-article.pdf));
- `lorem-slides.md` ([generated beamer slides](lorem-slides.pdf)); and
- `lorem-html.md` ([generated webpage](lorem-html.html)).

These can be converted to LaTeX article, beamer slides, or html web page, respectively, using the following command: `mdfile filename.md`. Yaml front matter for the three files are shown below.

#### YAML front matter for `lorem-article.md`

```txt
---
to: pdf

---
```

#### YAML front matter for `lorem-slides.md`

```txt
---
to: beamer

---
```

#### YAML front matter for `lorem-html.md`

```txt
---
to: html

---
```

#### MDfile Options

Mdfile supports the following options.

```txt
usage: mdfile2.py [-h] [-o OUTPUT] [-f FORMAT] [--no-output-file] [-i]
                  [--version] [-v] [-d] [-l] [--debug-file] [--debug-render]
                  [--render-file RENDER_FILE] [--template-file TEMPLATE_FILE]
                  [--include-in-header [INCLUDE_IN_HEADER [INCLUDE_IN_HEADER ...]]]
                  [--bibliography BIBLIOGRAPHY] [--css [CSS [CSS ...]]]
                  [--csl CSL] [--highlight-style HIGHLIGHT_STYLE]
                  [--yaml [YAML [YAML ...]]] [--do-not-preprocess-mustache]
                  [--slide-level SLIDE_LEVEL] [--pdf-engine PDF_ENGINE]
                  [--templating-engine TEMPLATING_ENGINE]
                  mdfile

positional arguments:
  mdfile                MD file. Options specified on commandline override
                        those specified in the file yaml block.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output path. A file or dir name can be specified.
  -f FORMAT, --format FORMAT
                        Output format: html, pdf, beamer, latex.
  --no-output-file      Use this flag to turn off creating an output file.
  -i, --ignore-times    Forces the generation of the output file even if the
                        source file has not changed
  --version             show program's version number and exit
  -v, --verbose         Turn verbose on.
  -d, --debug           Log debugging messages.
  -l, --log             Writes out a log file.
  --debug-file          Debug messages regarding file loading.
  --debug-render        Debug messages regarding template rendering.
  --render-file RENDER_FILE
                        Path to render file (used for html only).
  --template-file TEMPLATE_FILE
                        Path to pandoc template file.
  --include-in-header [INCLUDE_IN_HEADER [INCLUDE_IN_HEADER ...]]
                        Path to file that will be included in the header.
                        Typically LaTeX preambles.
  --bibliography BIBLIOGRAPHY
                        Path to bibliography file.
  --css [CSS [CSS ...]]
                        Space separated list of css files.
  --csl CSL             csl file, only used when a bibfile is specified either
                        via commandline or via yaml frontmatter
  --highlight-style HIGHLIGHT_STYLE
                        Specify a highlight-style. See pandoc --list-
                        highlight-styles.
  --yaml [YAML [YAML ...]]
                        Space separated list of extra yaml files to process.
  --do-not-preprocess-mustache
                        Turns off pre-processesing md file using mustache
                        before converting via pandoc.
  --slide-level SLIDE_LEVEL
                        Slide level argument for pandoc (for beamer documents)
  --pdf-engine PDF_ENGINE
                        PDF engine used to generate pdf. The default is
                        vanilla LaTeX. Possible options are lualatex or tetex.
  --templating-engine TEMPLATING_ENGINE
                        Specify whether to use mustache or jinja2 engine.
                        Jinja2 is the default choice.
```

##### Template option

Use template option to specify a particular pandoc template that will be used during document conversion.

##### Render option

This option is only available when converting mardown to html documents.  When a render file is specified, the contents of the markdown file are available in the rendering context body tag during the rendering operation.  MDfile supports both mustache and jinja2 renderers.  template file is ignored when render file is specified.

##### Mustache preprocessing

Mustache preprocessing can be used to render yaml front matter using mustache renderer.  When converting to html, mustach preprocessing can also be used for converting mark down file contents before sending these contents to pandoc conversion.  Mustache preprocessing occurs before contents are sent to pandoc for conversion.

##### Yaml files

Information stored in external yaml files is available as the rendering context during the rendering operatiion.

## Webify Utility

Webify is a static site generator utility.  It uses mdfile utility to convert markdown files to html pages, LaTeX articles, or beamer slides.  Webify utility traverses a directory tree and performs markdown files' conversion according to file-specific rendering context.  Rendering context for each file is constructed using information found in:

- [A] Yaml files in ancestor folders (up to the root directory); and
- [C] Yaml files in the current folder; and
- [F] Yaml front matter found in the current file.

In case of key collisions, the following preference ordering is used: A < C < F.

### Example

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
web_title: Webify test site
name: Winnie
```

and the contents of `a.yaml` file are:

```
---
name: Tigger
author: Bugs bunny
```

and the contents of `a.md` file are:

```
---
name: Forest
title: A simple story 
---
Important stuff.
```

then the rendering context for `a.md` will be:

```
web_title: Webify test site
author: Bugs bunny
name: Forest
title: A simple story 
```

### A note about loading yaml files

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

### A note about yaml front matter

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

### The `_partials` folder

Any folder can contain a special sub-folder, called `_partials`.  Each time webify processes a folder, it first looks whether or not the folder contains a sub-folder, called `_partials`.  If a `_partials` sub-folder is found, then items within this folder are processed.  Items within the `_partials` sub-folder are available added to the rendering context for its parent folder.  This allows a mechanism to create common web-snippets, such as headers, footers, and navigation items, that can be used in any file that is stored in this (the parent) folder or one of its sub-folders.

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

Here, the rendering context for `index.md` file includes the entries, `footer_html`, `header_html`, and `nav_md`.  Each of these entries correspond to processed `footer.html`, `header.html`, and `nav.md` file contents.

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

### Copying source markdown files to the destination

Webify's default behavior is to process markdown files to create 1) LaTeX articles, 2) beamer slides, or 3) html pages.  This means that webify does not copy the source markdown file to the destination.  E.g., a markdown files `example.md` will be appear as either `example.pdf` (cases 1 and 2) or `example.html` (case 3) at the destination location.  Sometimes however it is desireable to copy the source markdown file to the destination location.  This can be achieved by using the `copy-source` flag in the yaml front matter as follows.

```txt
---
copy-source: True

---
File contents ...
```

The [markdown source](lorem-html.md) for this [html](lorem-html.html) file was copied using this mechanism.  Without this flag, `lorem-html.md` will not be available in the desitnation folder.

## Webify options

Webify supports the following options.

```
usage: webify2.py [-h] [--version] [-v] [-d] [--debug-rc] [--debug-db]
                  [--debug-db-ignore] [--debug-yaml] [--debug-render]
                  [--debug-md] [-l] [-i] [--force-copy] [-t TEMPLATING_ENGINE]
                  srcdir destdir

positional arguments:
  srcdir                Source directory
  destdir               Destination directory

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         Prints helpful messages
  -d, --debug           Turns on (global) debug messages
  --debug-rc            Turns on rendering context debug messages
  --debug-db            Turns on file database debug messages
  --debug-db-ignore     Turns on .webifyignore debug messages
  --debug-yaml          Turns on yaml debug messages
  --debug-render        Turns on render debug messages
  --debug-md            Turns on mdfile debug messages
  -l, --log             Use log file.
  -i, --ignore-times    Forces the generation of the output file even if the
                        source file has not changed
  --force-copy          Force file copy.
  -t TEMPLATING_ENGINE, --templating-engine TEMPLATING_ENGINE
                        Specify whether to use mustache or jinja2 engine.
                        Jinja2 is the default choice.
```

## Blogging

Webify version > 3.1 supports blogging.  When blogging is enabled for a folder, all markdown files in this folder and all its descended sub-folders are collected and added to a blogging rendering context.  A special blog index markdown file is processed last, and the blogging rendering context is available to create a blog index.

Consider the following yaml file that sits in folder `blog-example`

```txt
---
blog: True
blog_title: Example Blog
blog_index: index.md
```

This file indicates that folder `blog-example` sets up a blog.  It also identifies a markdown file that will serve as the blog index.  All other markdown files in this folder and in all its descendent folders will be posts.  The contents of `index.md` file are:

```python
---
render: "{{__root__}}/_templates/simple_blog.jinja"

---

```

In this case the `index.md` file simply identifies the jinja template shown below:

```jinja2
<!DOCTYPE html>
<html lang="en">
  <head>
  </head>
  <body>
    <div class="container">
        <h1>{{ blog_title }}</h1>

        <h2>Posts</h2>

        <ul>
            {% for post in blog_posts %}
                <li><a href="{{ post.link }}">{{ post.title }}</a></li>
            {% endfor %}
        </ul>

    </div>
  </body>
</html>
```

Webify will process markdown files in folder `blog-example` and all its descendent folders and set up the rendering context that can be used when generating blog index as shown above.

The generated blog is found [here](blog-example/index.html).