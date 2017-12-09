FROM ubuntu:16.04

RUN apt-get update
RUN apt-get install -y texlive-full
RUN apt-get upgrade -y
RUN apt-get install -y python-pip python-dev build-essential
RUN pip install --upgrade pip 

RUN apt-get install -y haskell-platform
RUN apt-get install  -y pandoc
RUN pip install numpy
RUN pip install pyyaml
RUN pip install pystache
RUN pip install pypandoc
RUN pip install watchdog