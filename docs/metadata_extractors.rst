Overview
========

With version 2.2.0 of Declad, we add support for metadata extractor
scripts. This allows data files to be dropped into the dropbox directory
**without** matching .json metadata files, at which point Declad will
call a metadata extractor script (if one is configured) on those files
to have that script generate metadata files for those data files. Once
the metadata file appears, Declad will proceed to decalare and upload
the files as normal.

Several points: \* This is only supported in the “local” scanner
configuration, we do not support remote / xrootd metadata extraction. \*
There is one metadata extractor script allowed per Declad instance, if
there are multiple types of files that need metadata generated/extracted
the one script must handle all those types. \* There is a delay (between
one and two scanner intervals) before the extractor is called, to see if
a metadata file is going to show up in the dropbox, so one may want to
adjust the scanner intervals appropriately.

Script Information
==================

The metadata extractor script is called with up to 50 filenames on its
command line; its jobs is to generate a filename.json for each file it
is given.

Example script (the referred to scripts “sam_cleanup” and “log_metadata”
are left as an exercise) :

::

   #!/bin/sh

   for fname in "$@"
   do
       if [ -r ${fname}.json ] 
       then
       :  # metadata already exists,  do nothing
       else
           # message for log
           echo "$(date -u) demo-metadata-extractor: generating ${fname}.json"

           # get size and checksum...
           fsize=$(stat --format '%s' ${fname})
       chksum=$(xrdadler32 ${fname} | sed -e 's/ .*//')
          
           # choose file format, and run extra extraction, based on filename
           extra=""
           format="unknown"
           case $fname in
           *.txt)      format=txt;;
           *.log)      format=log;  extra="$(log_metadata ${fname})";;        
           *.art.root) format=art;  extra="$(sam_metadata_dumper ${fname} | sam_cleanup)" ;;
           *.root)     format=root;;
           esac

           # actually write metadata
           cat > ${fname}.json <<EOF
   {
       "name": "$(basename $fname)",
       "namespace": "hypotpro",
       "size": $fsize,
       "checksums": {"adler32": "$chksum"},
       "metadata": {
           ${extra}
           "file.format": "$format"
       }
   }
   EOF

     fi
   done
