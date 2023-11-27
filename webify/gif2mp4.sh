#!/bin/bash

for file in $@; do
    if [ "${file: -4}" == ".gif" ]; then
        echo "Converting $file to ${file%.gif}.mp4"
        ffmpeg -i $file -movflags faststart -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"  -pix_fmt yuv420p ${file%.gif}.mp4
    else
        echo "Ignoring $file.  Not a gif file"
    fi
done

