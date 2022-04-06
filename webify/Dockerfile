FROM python:3.9

RUN apt-get update -y
RUN apt-get upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-full
RUN apt-get install -y pandoc

ADD . /webify
RUN pip3 install -r /webify/requirements.txt

ENV WEBIFY_DIR=/webify
ENV WEBIFY_PYTHON=python3
ENV DISPLAY=:0
ENV PATH=$PATH:/webify

WORKDIR /webify

CMD ['/bin/sh']