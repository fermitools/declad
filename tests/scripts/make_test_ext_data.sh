#!/bin/sh

#
# make dummy datafiles to test declad for use with demo_metadata_extractor
# -- this time with *new* metadata...
#

ds=$(date +%s)

for i in 1 2 3 4 5
do


fname="hypotpro_declad_test_${ds}_${i}.txt"
dropbox=/home/hypotpro/declad_848/dropbox

cat > ${dropbox}/${fname} <<EOF
test file $fname
EOF

done
