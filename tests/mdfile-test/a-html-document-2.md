---
to: html
foo: "{{{__version__}}}"
render: 
preprocess-frontmatter: True
preprocess-buffer:  
highlight-style: kate
highlight_style: kate
renderer: jinja2

---

Version: {{{__version__}}}

Filepath: {{{__filepath__}}}

Rootdir: {{{__root__}}}

Version through yaml frontmatter: {{foo}}

{{highlight-style}}