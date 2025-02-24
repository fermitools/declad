#!/bin/sh

#
# make dummy datafiles to test declad for use with demo_metadata_extractor
#

dropbox=/home/hypotpro/declad_848/dropbox

if [ "$1" = "--subdirs" ]
then
	subdirs=true
else
	subdirs=false
fi
ds=$(date +%s)

for i in 1 2 3 4 5
do

fname="hypotpro_declad_test_${ds}_${i}.txt"

if $subdirs
then
    # two-digit subdirectory
    mkdir $dropbox/${i}${i}
    sfname="${i}${i}/$fname"
else
    sfname="$fname"
fi

cat > ${dropbox}/${sfname} <<EOF
test file $fname
EOF

done
