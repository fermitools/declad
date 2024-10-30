#!/bin/sh

#
# make dummy datafiles to test declad.
# -- this time with *new* metadata...
#

ds=$(date +%s)

for i in 1 2 3 4 5
do


fname="$i$i/hypotpro_declad_test_${ds}_${i}.txt"
dropbox=/home/hypotpro/declad_848/dropbox

mkdir ${dropbox}/$i$i

cat > ${dropbox}/${fname} <<EOF
test file $fname
EOF

fsize=$(stat --format '%s' ${dropbox}/${fname})
chksum=$(xrdadler32 ${dropbox}/${fname} | sed -e 's/ .*//')

# adding just the minmium metadat to make our declad_config happy
cat > ${dropbox}/${fname}.json <<EOF
{
"name": "$fname",
"namespace": "hypotpro",
"size": $fsize,
"checksums": {"adler32": "$chksum"},
"metadata": {
    "dh.type": "other",
    "rs.runs": [1000001],
    "fn.tier": "etc",
    "fn.format": "txt",
    "fn.owner": "hypotraw",
    "fn.description": "declad_test3",
    "fn.configuration": "c20240226",
    "core.runs":[1000001], 
    "core.run_type": "test",
    "core.file_type": "test"
    }
}
EOF

done
