# Installation

Install pandoc and LaTeX

~~~
python3 -m venv ~/venv/webify
source activate ~/venv/webify/bin/activate
pip3 install -r requirements2.txt
~~~

Add the following to .bashrc 

~~~
export WEBIFY_DIR=~/webify/webify
export WEBIFY_PYTHON=~/venv/webify/bin/python3
~~~