FROM ubuntu

RUN apt-get update -y
RUN apt-get upgrade -y 
RUN apt-get install -y python3-venv python3-dev build-essential python3-pip
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-full
RUN apt-get install -y pandoc
COPY . /app
RUN pip3 install -r /app/requirements.txt
