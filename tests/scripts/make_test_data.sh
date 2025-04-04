#!/bin/sh

#
# make dummy datafiles to test declad.
#

ds=$(date +%s)

for i in 1 2 3 4 5
do


fname="etc_txt_hypotpro_declad_test_c20240219_$ds$i.txt"
dropbox=/home/hypotpro/declad_848/dropbox
dropbox=/tmp/dropbox

cat > ${dropbox}/${fname} <<EOF
test file $fname
EOF

fsize=$(stat --format '%s' ${dropbox}/${fname})
chksum=$(xrdadler32 ${dropbox}/${fname} | sed -e 's/ .*//')

# adding just the minmium metadat to make our declad_config happy
cat > ${dropbox}/${fname}.json <<EOF
{
"file_name": "$fname",
"file_size": $fsize,
"checksum": ["adler32:$chksum"],
"file_format": "txt",
"file_type": "other",
"runs": [ [1,1,"test"]],
"data_tier": "etc",
"dh.owner": "hypotpro",
"dh.description": "declad_test",
"dh.configuration": "c20240226"
}
EOF

done
