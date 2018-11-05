---
to: html
foo: "{{{__version__}}}"
render: render-1.html
preprocess-mustache: True
renderer: jinja2
names:
    - bo
    - faisal
    - john
    - murduk
    - gazabani
    - michael

---

# A PDF file

![Figure 2 caption](img2.png)

This pdf document is created from `a-pdf-document.md`.  It supports both code highlighting and LaTeX math notation.

~~~python
x = 2
print 'The value of x is', x
~~~

and some maths

$$
E = mc^2
$$

![Figure 1 caption](img1.png|img2.png |img3.png| img4.png | img5.png)   
![Figure 3 caption](img3.png)  
![Figure 4 caption](img4.png)

# This man is my mentor.

Version: {{{__version__}}}

Filepath: {{__filepath__}}

Rootdir: {{__rootdir__}}

Version through yaml frontmatter: {{foo}}
