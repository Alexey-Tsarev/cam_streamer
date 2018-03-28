#!/usr/bin/env sh

wget https://github.com/jkulesza/usbreset/raw/master/usbreset.c
gcc -o usbreset usbreset.c
rm usbreset.c
