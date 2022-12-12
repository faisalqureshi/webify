#!/bin/bash

docker run -it \
       --user $(id -u):$(id -g) \
       --volume=$(pwd):/src  \
       --volume=/Users/faisal/Sites:/dst \
       webify:0.5 bash
