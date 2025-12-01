# Webify

A python static site generator using information stored in yaml files.  It is
designed to process: html, markdown, and jupyter notebook files.  It can be
used to generate an entire site or perform markdown to html/LaTeX/Beamer conversion.  Check [here](http://vclab.science.uoit.ca/webify-manual/introduction.html) for more information.  [My website](http://faculty.uoit.ca/qureshi) is generated using this utility.  Most of my course websites are
also generated using this tool.

[![Latest Release](https://img.shields.io/github/v/release/faisalqureshi/webify?sort=semver)](https://github.com/faisalqureshi/webify/releases/latest)

# Installation

- **Webify >= 3.0 uses Python 3**  (Dec 9, 2019)

## Instructions

Webify requires pandoc (version > 1.19) and LaTeX (for pdf generation).  Follow the OS specific instructions for installing pandoc and LaTeX.  Below I provide instructions for OSX.

### OSX

#### Setting up Python, TeX and pandoc

Install Homebrew first. Check [https://docs.brew.sh/Installation](https://docs.brew.sh/Installation).

Although, Mac comes with Python3, I prefer to install it within homebrew

~~~bash
$ brew install python3
~~~

Next, install MacTeX available at [https://www.tug.org/mactex/mactex-download.html](https://www.tug.org/mactex/mactex-download.html)

Install pandoc using brew 

~~~bash
$ brew install pandoc
~~~

#### Installing webify and configuring commandline usage

Now clone webify in your home folder 

~~~bash
$ git clone git@github.com:faisalqureshi/webify.git
~~~

Create a Python3 environment that you will use for webify.  Before doing the following I confirm that `python3` points to brew installation.

~~~bash
$ python3 -m venv ~/venv/webify
$ source activate ~/venv/webify/bin/activate
$ pip3 install -r requirements2.txt
~~~

Add the following to environment.  E.g., I am using zsh, so I added the following to  `.zshrc`

~~~txt
export WEBIFY_PYTHON=/Users/faisal/venv/webify/bin/python
export WEBIFY_DIR=/Users/faisal/webify/webify
export PANDOC_TEMPLATES=/Users/faisal/Dropbox/Templates/pandoc

export PATH=$WEBIFY_DIR:$PATH
~~~

You may have to restart the terminal to ensure the environment variables  are captured.   You can now test the installation as follows:

~~~bash
$ mdfile
usage: mdfile2.py [-h] [-o OUTPUT] [-f FORMAT] [-i] [--standalone-html] [--do-not-create-output-file] [--version] [-v] [-d] [-l] [--debug-buffer] [--debug-file] [--debug-render] [--debug-timestamps] [--debug-rc]
                  [--debug-pandoc] [--render-file RENDER_FILE] [--template-file TEMPLATE_FILE] [--include-in-header [INCLUDE_IN_HEADER ...]] [--bibliography [BIBLIOGRAPHY ...]] [--css [CSS ...]] [--csl CSL]
                  [--highlight-style HIGHLIGHT_STYLE] [--yaml [YAML ...]] [--do-not-preprocess-frontmatter] [--do-not-preprocess-buffer] [--slide-level SLIDE_LEVEL] [--pdf-engine PDF_ENGINE] [--renderer RENDERER]
                  [--pandoc-var PANDOC_VAR] [--pandoc-meta PANDOC_META]
                  mdfile
mdfile2.py: error: the following arguments are required: mdfile
~~~

and 

~~~bash
$ webify
usage: webify2.py [-h] [-i] [--force-copy] [--version] [-v] [-d] [-l] [--debug-rc] [--debug-dirlist] [--debug-db] [--debug-db-ignore] [--debug-yaml] [--debug-render] [--debug-md] [--debug-html]
                  [--debug-availability] [--debug-ignore] [--debug-live] [--debug-next-run] [--debug-nb] [--debug-nb-settings] [--show-availability] [--show-not-compiled] [--show-not-copied] [--show-compiled]
                  [--show-ignored] [--live] [--upload-script UPLOAD_SCRIPT] [--live-url-prefix LIVE_URL_PREFIX] [--renderer RENDERER] [--pandoc-var PANDOC_VAR] [--pandoc-meta PANDOC_META]
                  srcdir destdir
webify2.py: error: the following arguments are required: srcdir, destdir
~~~

### Linux

The installation on Linux is similar, except that instead of brew we will use apt-get to install the relevant packages.  The recipe is as follows:

1. Install python3
2. Install TeX
3. Install pandoc ([https://pandoc.org/installing.html](https://pandoc.org/installing.html))
 
Now follow instructions in "Installing webify and configuring commandline usage" above.

### Windows

You can install webify on window using the WSL shell running, say Ubuntu or you can use [MinGW64](https://www.mingw-w64.org/).  MinGW64 has tigher integration with the window subsystem, so I prefer that.  

MingW64 using [pacman](https://wiki.archlinux.org/title/pacman) package manager to install applications.  Check [https://packages.msys2.org/package/](https://packages.msys2.org/package/) for available packages.  Here's a recipe.

1. Install [Python from Windows Store](https://apps.microsoft.com/detail/9PJPW5LDXLZ5?hl=en-US&gl=US).
2. Install TeX from [MikTeX](https://miktex.org/)
3. Install pandoc

Now follow instructions in "Installing webify and configuring commandline usage" above.

# Questions or Comments

Please contact Faisal Qureshi at <a href="mailto:faisal.qureshi@ontariotechu.ca">faisal.qureshi@ontariotechu.ca</a>. 
