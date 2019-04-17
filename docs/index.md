---
render: "{{root}}/_templates/index.mustache"

---

# Versions

## v1.8.1

- Support for PANDOC_TEMPLATES environment variable.
- Preprocess md files via Mustache before passing these off to pandoc converter.

## v1.8

- Introducing media filters.

## v1.7

- YAML front-matter in md files is now available as context during rendering.

## v1.6 Initial release

# Introduction

Webify is a Python tool for creating static websites and PDF documents from HTML and markdown files.  It is similar to static site generators, such as [Hugo](https://gohugo.io/) and [Jekyll](https://jekyllrb.com/).  However, Webify has far fewer features (I believe), and it is probably much much slower.  The upside is that Webify code is much easier to understand.  It is also fast enough for my needs.

My primary motivation for writing Webify is to be able to use plaintext (markdown) for website.  Jeykyll and Hugo are very good; however, I wanted something even simpler.  I consider Webify the "hello world" of static site generators.  A secondary motivation was to move my document generation work flow (course slides, assignments, etc.) to [pandoc](https://pandoc.org/).  You can think of Webify as a wrapper around pandoc.  Webify sort of automates website and PDF documents generation.  I have recently dockerized Webify, so now we can use it on any machine that supports docker.

## Example sites

I have used Webify to generate the following sites:

- [http://faculty.uoit.ca/qureshi](http://vclab.science.uoit.ca)
- [Simulation and modeling](http://csundergrad.science.uoit.ca/courses/2017-fall/csci3010u/)
- [Advanced topics in high-performance computing](http://csgrad.science.uoit.ca/courses/mcsc-ml/)

This documentation is also generated using webify.

## Usage

Webify supports templating through [Mustache](https://mustache.github.io/).  Context for Mustache is stored in [YAML](http://yaml.org/) data files.

Webify is used as follows:

~~~bash
python webify.py /path-to/src-folder /path-to/dest-folder
~~~

This will populate the destination folder with the generated website.  You can then use 'rsync' or something similar to upload to the contents of the destination folder to your favorite web hosting site.

## How does it work?

At its core, Webify renders html and markdown files using mustache templates and data stored in yaml files.  Markdown files are rendered via pandoc through pypandoc.  Currently the following four options are supported:

1. Markdown file is converted into an HTML snippet, which as incorporated into a Mustache template;
2. Markdown file is converted to a standalone HTML file;
3. Markdown file is converted to a PDF file; and
4. Markdown file is converted into a beamer slideshow (PDF).

Yaml front matter included in a Markdown file is used to control how a Markdown file will be converted.

### Example yaml header for option 1 above

~~~txt
---
render: /path/to/mustache/template/file
~~~

In this case the contents of this markdown files replace the '{{{body}}}' tag of mustache template.

### Example yaml header for option 2 above

~~~txt
---
template: /path/to/optional/pandoc/html5/template/file
~~~

This is akin to using the following pandoc command

~~~bash
pandoc -t html5 --mathjax --highlight-style=pygments this-file.md -o this-file.html
~~~

### Example yaml header for option 3 above

~~~txt
---
to: pdf
template: /path/to/optional/pandoc/latex/template/file
~~~

This is akin to using the following pandoc command

~~~bash
pandoc -t latex --mathjax --highlight-style=kate -V graphics:true this-file.md -o this-file.pdf
~~~

or

~~~bash
pandoc --template=/path/to/optional/pandoc/latex/template/file --mathjax --highlight-style=kate -V graphics:true this-file.md -o this-file.pdf
~~~


### Example yaml header for option 4 above

~~~txt
---
to: beamer
template: /path/to/optional/pandoc/beamer/template/file
~~~

This is akin to using the following pandoc command

~~~bash
pandoc -t beamer --mathjax --highlight-style=kate -V graphics:true this-file.md -o this-file.pdf
~~~

or

~~~bash
pandoc --template=/path/to/optional/pandoc/beamer/template/file --mathjax --highlight-style=kate -V graphics:true this-file.md -o this-file.pdf
~~~

## Folder `/_partials`

The `_partials` is used to store HTML, markdown and YAML files that can be used to create html snippets, which will be available to every markdown and html file during rendering.

For example, a `_partial` folder might contain the following files:

- nav.yaml
- nav.md
- footer.html
- header.html

It is possible to include the contents of the rendered nav.md, footer.html and header.html files using `{{{nav_md}}}`, `{{{footer_html}}}` and `{{{header_html}}}` mustache keys.

## .webifyignore

Use .webifyignore file to indicate which files folders should *not* be processed.  For example:

`*~`  
`.DS_Store`
`index.yaml`  
`_tmp`

Internally, `fnmatch` is used to find matching files/folders.

## A note about yaml files

YAML files are used to specify the data that is avaiable during mustache rendering.  Data in a YAML file is available to every html/mustache file present in the current folder and all of its subfolders.

## Converting markdown files to pdf documents

`mdfile.py` can be used as a standalone utility to convert a markdown file into a PDF documents.  It uses `pandoc` to perform the actual conversion.  Yaml frontmatter can be used to specify options for pandoc.  Check out the source code for `mdfile.py` for supported tags.  Here's a sample [pdf](layered-architecture.pdf) file generated from this [markdown](layered-architecture.md) file.

## Copying markdown files to destination

Sometimes it is desirable to copy markdown files to the destination.  Default behavior is to *not* copy the markdown files.  This behavior can be overwritten using the following yaml frontmatter.

~~~yaml
---
copy-to-destination: True
~~~

## Processing markdown files using Mustache before conversion using PANDOC_TEMPLATES

~~~yaml
---
preprocess-mustache: True
~~~

## Installing webify

Check out the installation information available with the source code.

<!-- ## Media Filters -->

<!-- Media filters are MD preprocessors that can be used to convert markdown image tag `![This is image caption](images.jpg)` to html code before pandoc conversion.  This allows one to use arbitrary html code for displaying images and videos.  It is also possible to generate a picture or a movie grid display by specifying multiple files `![This is image caption](images.jpg|images.jpg)`.  How the image tag is converted to markdown is controlled by mustache templates. -->

<!-- **IMPORTANT** Use the `--media-filter` command line option to turn on media filtering. -->

<!-- Check out media filter in action [here](media-filters/demo.html), and the corresponding md file is [here](media-filters/demo.md). -->
