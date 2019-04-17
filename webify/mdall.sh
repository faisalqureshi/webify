#!/bin/bash

for file in $@
do
    echo Processing $file
    mdfile $file
done
