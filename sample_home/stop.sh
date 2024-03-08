#!/bin/sh

if [ -r logs/declad.pid ]
then
    kill $(<logs/declad.pid)
    rm logs/declad.pid
fi
