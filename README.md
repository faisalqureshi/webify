# Webify

A python static site generator using information stored in yaml files.  It is
designed to process: html, markdown, and jupyter notebook files.  It can be
used to generate an entire site or perform markdown to html/LaTeX/Beamer conversion.  Check [here](http://vclab.science.uoit.ca/webify-manual/introduction.html) for more information.

[My website](http://faculty.uoit.ca/qureshi) is generated using this utility.  Most of my course websites are
also generated using this tool.

The utility uses pandoc for most of the heavy lifting.  Pandoc and LaTeX version information for this version of webify is included below.

## Pandoc

~~~
pandoc 2.17.1.1
Compiled with pandoc-types 1.22.1, texmath 0.12.4, skylighting 0.12.2,
citeproc 0.6.0.1, ipynb 0.2
~~~

## LaTeX

~~~
pdfTeX 3.14159265-2.6-1.40.21 (TeX Live 2020)
kpathsea version 6.3.2
Copyright 2020 Han The Thanh (pdfTeX) et al.
There is NO warranty.  Redistribution of this software is
covered by the terms of both the pdfTeX copyright and
the Lesser GNU General Public License.
For more information about these matters, see the file
named COPYING and the pdfTeX source.
Primary author of pdfTeX: Han The Thanh (pdfTeX) et al.
Compiled with libpng 1.6.37; using libpng 1.6.37
Compiled with zlib 1.2.11; using zlib 1.2.11
Compiled with xpdf version 4.02
~~~
