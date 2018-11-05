---
to: html
foo: "{{{__version__}}}"
render: render-1.html
preprocess-mustache: True

---

Version: {{{__version__}}}

Filepath: {{{__filepath__}}}

Rootdir: {{{__rootdir__}}}

Version through yaml frontmatter: {{foo}}

