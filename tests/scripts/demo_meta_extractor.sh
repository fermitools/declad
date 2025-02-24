#!/bin/sh

#
# make dummy datafiles to test declad.
# -- this time with *new* metadata...
#

ds=$(date +%s)
dropbox=/home/hypotpro/declad_848/dropbox

for fname in $*
do
    if [ -r ${fname}.json ] 
    then
	:
    else
	echo "$(date -u) demo-metadata-extractor: generating ${fname}.json"

	case $fname in
	/*) ;;
	*) fname=$drobpox/$fname
	esac

        # adding just the minmium metadata to make our declad_config happy

	fsize=$(stat --format '%s' ${fname})
	chksum=$(xrdadler32 ${fname} | sed -e 's/ .*//')
	cat > ${fname}.json <<EOF
{
"name": "$(basename $fname)",
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
    "fn.configuration": "c20240226"
    }
}
EOF

    fi
done
