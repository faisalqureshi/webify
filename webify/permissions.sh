#!/bin/bash

if [ $# -ne 1 ]
then
   	echo "Usage: permissions.sh <foldername>"
else
	find $1 -type f -exec chmod 644 {} \;
	find $1 -type d -exec chmod 755 {} \;
fi
