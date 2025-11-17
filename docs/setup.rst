Setting up Declad
=================

Overview
--------

To run a declad instance, you will need:
* an account to run the service under
* the software and dependencies
* A suitable credential (like an x509 service/host certificate, and/or a refreshed Scitoken via
the `Managed Token Service <https://fifewiki.fnal.gov/wiki/Managed_Tokens_Service>`__) for
authentication
* a working rucio installation with suitable client configuration file
* a working metacat installation with suitable client configuration
* a cron job or similar to refresh metacat tokens
* a declad config file

This document will describe each of these in more detail.

An account
----------

You will probably run this service under a custom account name, and
configure the system in a directory in the home account.

Here at Fermilab we tend to use, for an experiment named “hypot” either
the “hypotpro” or “hypotraw” account.

As an account who can sudo, do: sudo useradd -u userid accountname

and setup suitable login permissions (.k5login here at Fermilab,
.ssh/authorized_keys as appropriate elsewhere)

[You can find the userid onsite at Fermilab by using wget or curl to
fetch http://www-giduid.fnal.gov/cd/FUE/uidgid/uid.lis and looking for
it (upper case), or by looking on any of the central gpvm cluster
machines for that experiment.]

A credential
------------

Currently Declad is setup to use a host/service x509 certificate for all
its authentication needs, and it assumes you will use some external
script to refresh the metacat/data-dispatcher token from that
credential. We hope in future to also allow SciTokens, so if you have a
service that refreshes SciTokens for other services, (i.e. our Managed
Token Service) you could use it here, and it’s easiest to use SciTokens
for authentication for the file transfers as you do not need extra
configuration on the fileservers to allow that credential in.

Installing the software
-----------------------

At the moment, the preferred way to install declad is with Spack and the
recipes in the fermi SCD_Recpies repository. However, the dependencies
are all Python, and so one could install them all in a virtualenv, or
with pip install –user.

Installing with Spack
~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

   <pre>
   wget https://github.com/FNALssi/fermi-spack-tools/raw/v2_21_0/bin/bootstrap
   sh bootstrap $HOME/packages
   . $HOME/packages/setup-env.sh
   spack buildcache list -al declad
   spack install --cache-only declad/<i>hash-from-above</i>
   </pre>

If there is an error with the gcc compiler version, edit the
``$SPACK_ROOT/etc/spack/compilers.yaml`` file, duplicate the gcc-11.4.1
section, and change one of the sections to version 11.3.1.

If there is an error with the gpg key, do
``spack buildcache keys --install --trust --force``.

For other installation options, see the bottom of this article.

“custom” directory
------------------

Either in the software package area, or in a local directory to the user
account, The two options are described below.

configure software custom directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

   <pre>
   spack cd -i declad
   cd declad/custom
   ln -s dune.py __init__.py
   </pre>

create a “custom” directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you’re planning to make site-local customizations, you want to do
this. Somewhere you’re putting such things make a “custom” directory,
and copy the custom/dune.py from the spack package, like:

.. raw:: html

   <pre>
     mkdir custom
     cp $(spack location -i declad)/custom/dune.py $HOME/custom/dune.py
     ln -s $HOME/custom/dune.py $HOME/custom/__init__.py
   </pre>

create a rucio config
---------------------

.. raw:: html

   <pre>
   mkdir -p $HOME/rucio_config/etc
   vi $HOME/rucio_config/etc/rucio.cfg
   </pre>

.. raw:: html

   <pre>
   [client]
   rucio_host = https://<i>xyz</i>-rucio.fnal.gov
   auth_host = https://<i>xyz</i>-rucio.fnal.gov

   ca_cert = /etc/grid-security/certificates
   account = <i>xyz</i>pro
   auth_type = x509
   client_cert = /home/<i>xyz</i>pro/certs/<i>xyz</i>-declad-cert.pem 
   client_key  = /home/<i>xyz</i>pro/certs/<i>xyz</i>-declad-key.pem
   </pre>

This of course needs to be edited for your experiment’s rucio service
and home directory.

Create a start.sh
-----------------

Now you want a start script to start your service; it needs to access
your spack area or virtualenv to find the software, and set the
environment variables to access the rucio and metacat instances,
something like:

.. raw:: html

   <pre>
   #!/bin/sh

   # find the software
   # . /path/to/virtualenv/activate
   #
   # or
   . $HOME/packages/setup-env.sh
   dver=<i>2.0.4</i>
   spack load declad@$dver

   # config for MetaCat and Rucio
   export METACAT_SERVER_URL=<i>https://metacat.server:port/instance/app</i>
   export RUCIO_HOME=$HOME/rucio_config

   # find our $HOME/bin executables and $HOME/custom python files first
   export PYTHONPATH=$HOME:$PYTHONPATH
   export PATH=$HOME/bin:$PATH

   nohup declad.py -dc declad_config.yaml  < /dev/null > logs/nohup.out 2>&1 &
   echo $! > logs/declad.pid
   </pre>

Of course, for “dver” above, use the version number for declad that you
installed earlier.

Oh, and also

.. raw:: html

   <pre>mkdir $HOME/logs</pre>

so we have a place for all this output, and/or possibly symlink it to
some scratch partition where you have more room for logs.

For symmetry, you may also want a “stop.sh”, like:

.. raw:: html

   <pre>
   #!/bin/sh

   if [ -r logs/declad.pid ]
   then
       kill $(&lt;logs/declad.pid)
       rm logs/declad.pid
   fi
   </pre>

But it isn’t strictly necessary.

cronjob to refresh metacat authentication
-----------------------------------------

create a script metacat_refresh.sh

.. raw:: html

   <pre>

   # if you're using a proxy from that cert to authenticate file transfers refresh it:
   grid-proxy-init -cert $HOME/certs/<i>xyz</i>-declad-cert.pem -key $HOME/certs/<i>xyz</i>-declad-key.pem

   # if you're using a managed token to authenticate file transfers, refresh that
   export HTGETTOKENOPTS="--credkey=<i>xyz</i>pro/managedtokens/fifeutilgpvm01.fnal.gov"
   htgettoken -i <i>xyz</i> -r production -a htvaultprod.fnal.gov

   # now refresh your metacat login token, either using your cert, or your managed token.

   export METACAT_SERVER_URL=<i>https://metacat.host:port/xyz_meta_prod/app</i>
   export METACAT_AUTH_SERVER_URL=<i>https://metacat.host:authport/auth/xyz</i>
   metacat auth login -m x509 -c $HOME/certs/<i>xyz</i>-declad-cert.pem -k $HOME/certs/<i>xyz</i>-declad-key.pem <i>xyz</i>pro

   </pre>

And a cron entry for the refresh, and probably an entry to start the
service

.. raw:: html

   <pre>
   crontab -e 
   </pre>

.. raw:: html

   <pre>
   0 * * * * /path/to/metacat_refresh.sh > logs/refresh.out 2>&1
   @reboot /path/to/metacat_refresh.sh > logs/refresh.out 2>&1 ; /path/to/start.sh > logs/start.out 2>& 1
   </pre>

And finally, if you’re using token authentication older versions of
xrdcp for file transfers, you’ll need some wrappers in $HOME/bin to get
BEARER_TOKEN set to the current token, which look like:

bin/xrdcp:

.. raw:: html

   <pre>
   #!/bin/sh

   # run xrdcp, but with token authentication...

   uid=$(id -u)
   export BEARER_TOKEN=$(<${BEARER_TOKEN_FILE:-/var/run/user/$uid/bt_u$uid}) 

   /usr/bin/xrdcp "$@"

   </pre>

and similarly for xrdfs. These combined with having $HOME/bin in your
PATH in the start script, will have declad use these wrappers to set
BEARER_TOKEN to the latest token contents each time it gets run.

Test authentication setup
-------------------------

Now test the authentication setup:
* run the refresh script
* use the METACAT_SERVER_URL and RUCIO_HOME values in your start script to test:

.. raw:: html

   <pre> 
   . $HOME/packages/setup-env.sh
   spack load declad@<i>2.0.4</i>
   METACAT_SERVER_URL=<i>value_from_start.sh</i>  metacat auth whoami
   RUCIO_HOME=<i>value_from_start.sh</i> rucio whoami
   </pre>

(Use the version of declad you installed in the “spack load”) Both
should give your experiment production account name back.

configure declad_config.yaml
----------------------------

We will use vi (or your favorite editor) to create a declad_config.yaml
in the $HOME directory.

Note that templates like “rel_path_pattern” in the config take metadata
field names from the converted MetaCat metadata, not the SAM metadata
field names.

Example contents below:

for xrootd remote dropbox
~~~~~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

   <pre>

   # Format of Declad config file as concluded from perusing sources.

   debug_enabled: true              # debug messages in the log?
   default_category: "migrated"     # default metadata category for unexpected uncategorized metadata attrs
   destination_root_path: "/a/b/c"  # path part of $dst_url for templates, below also $path in same
   destination_server: "host:port"  # host part of $dst_url for templates, below
   source_root_path: "/x/y"         # path part of $src_url for templates, below
   source_server: "host:port"       # host part of $src_url for templates, below, use localhost for local dropbox

   copy_command_template:  "xrdcp $src_url $dst_url"                     # copy command 
   download_command_template: "xrdcp xrootd:$server$src_path $dst_path"  # metadata file download with $server $src_path, $dst_path
   delete_command_template: "xrdfs rm $path"                             # clean files out of Dropbox, with $server and $path 
   quarantine_location: /tmp/quarantine                                  # location for files / metadata that don't match, etc.

   create_dirs_command_template:   "xrdfs $server mkdir -p $path"

   min_file_size: 1000                                                   # minimum file size that declad will transfer, in bytes

   # uncomment these and change if you don't want these default values
   #history_db: history.sqlite                         # file to keep history
   #interval: 30                                       # scan interval
   #timeout: 30                                        # timeout for scans
   #lowercase_meta_names: False                        # convert metadata fields to lowercase
   #max_movers: 10                                     # max parallel copies
   #keep_interval: 24*3600                             # how long to keep files
   #low_water_mark: 5                                  # size of work queue to trigger new scans
   #stagger: 0.2                                       # time interval in seconds between consecutive transfer task starts
   meta_suffix: .json                                 # suffix for metadata file (I.e. metadata for Fred.xx is in Fred.xx.json) 

   metacat_dataset: (for custom/dune.py)                # dataset to put files in
   metacat_url:                                         # url to metacat service 

   rel_path_function:                                   # relative path function ("hash" or "template") for placing files
   # rel_path_pattern:                                  # template (using metadata fields) if you picked "template" above


   #logging
   log:                                                 # name of logfile
   error:                                               # separate error log file, defaults to log: value.

   rucio:
     dataset_did_template:                              # template for rucio dataset namespace:name
     declare_to_rucio: (True)                           # whether to declare to rucio
     target_rses: [list]                                # rse's to ask Rucio to forward dataset, above, towards
     drop_rse:                                          # dropoff rse that has the dst_url we're copying to, above.
     
   samweb:
     user:                                              # Sam credentials: username
     url:                                               # url for samweb instance
     cert:                                              # user x509 cert for authentication
     key:                                               # private key for above

   scanner:
     type: local                                        # scanner type: local or xrootd
     replace_location:                                  # replace Dropbox location with this in path for local scanner
     ls_command_template:    "xrdfs $server ls -l $location"               # directory listings: with $server and $location  
     parse_re:               "^(?P<type>[a-z-])\S+\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(?P<size>\d+)\s+(?P<path>\S+)$"                                      
                                                        # regexp for "ls" / "xrdfs" ls  output                                          
     filename_patterns:                                 # filename pattern(s) to watch for
     filename_pattern: *.hdf5

   web_gui:
     prefix:                                            # website url prefix for web monitor
     site_title: (Declaration Daemon)                   # website title for web monitor
     port: (8080)                                       # website port for monitor

   #graphite:                                           # for forwarding data to graphite service
   #        host: filer-carbon.cern.ch
   #        port: 2004
   #        namespace: fts.protodune.np04-srv-024-hd5 
   #        interval: 10
   #        bin: 60

   </pre>

for local directory dropbox
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

   <pre>

   # Format of Declad config file as concluded from perusing sources.

   debug_enabled: true              # debug messages in the log?
   default_category: "migrated"     # default metadata category for unexpeted uncategorized metadata attrs
   destination_root_path: "/a/b/c"  # path part of $dst_url for templates, below also $path in same
   destination_server: "host:port"  # host part of $dst_url for templates, below
   source_root_path: "/x/y"         # path part of $src_url for templates, below
   source_server: "localhost"       # host part of $src_url for templates, below, use localhost for local dropbox

   create_dirs_command_template: ":" # command template using $server and  $path, use ":" if destination auto-creates directories
   copy_command_template:  "xrdcp $src_url $dst_url"       # copy command 
   download_command_template: "cp $src_path $dst_path"     # metadata file download command, with $server $src_path, $dst_path
   delete_command_template: "rm $path"                     # clean files out of Dropbox, with $server and $path 

   quarantine_location: /tmp/quarantine                    # location for files / metadata that don't match, etc.

   min_file_size: 1000                                     # minimum file size that declad will transfer, in bytes

   # uncomment these and change if you don't want these default values
   #history_db: history.sqlite                         # file to keep history
   #interval: 30                                       # scan interval
   #timeout: 30                                        # timeout for scans
   #lowercase_meta_names: False                        # convert metadata fields to lowercase
   #max_movers: 10                                     # max parallel copies
   #keep_interval: 24*3600                             # how long to keep files
   #low_water_mark: 5                                  # size of work queue to trigger new scans
   #stagger: 0.2                                       # time interval in seconds between consecutive transfer task starts
   meta_suffix: .json                                 # suffix for metadata file (I.e. metadata for Fred.xx is in Fred.xx.json) 

   metacat_dataset:                                     # dataset to put files in
   metacat_url:                                         # url to metacat service 

   rel_path_function:                                   # relative path function ("hash" or "template") for placing files
   # rel_path_pattern:                                  # template (using metadata fields) if you picked "template" above


   #logging
   log:                                                 # name of logfile
   error:                                               # separate error log file, defaults to log: value.

   rucio:
     dataset_did_template:                              # template for rucio dataset namespace:name
     declare_to_rucio: (True)                           # whether to declare to rucio
     target_rses: [list]                                # rse's to ask Rucio to forward dataset, above, towards
     drop_rse:                                          # dropoff rse that has the dst_url we're copying to, above.
     
   samweb:
     user:                                              # Sam credentials: username
     url:                                               # url for samweb instance
     cert:                                              # user x509 cert for authentication
     key:                                               # private key for above

   scanner:
     type: local                                        # scanner type: local or xrootd
     replace_location:                                  # replace Dropbox location with this in path for local scanner
     ls_command_template: "ls -ln $location"                 # with $server and $location 
     parse_re:              "^(?P<type>[a-z-])\\S+\\s+\\d+\\s+\\d+\\s+\\d+\\s+(?P<size>\\d+)\\s+\\S.{11}\\s(?P<path>\\S+)$"                                          
                                                        # regexp for "ls" / "xrdfs" ls  output                                          
     filename_patterns:                                 # filename pattern(s) to watch for
     filename_pattern:

   web_gui:
     prefix:                                            # website url prefix for web monitor
     site_title: (Declaration Daemon)                   # website title for web monitor
     port: (8080)                                       # website port for monitor

   #graphite:                                           # for forwarding data to graphite service
   #        host: filer-carbon.cern.ch
   #        port: 2004
   #        namespace: fts.protodune.np04-srv-024-hd5 
   #        interval: 10
   #        bin: 60

   </pre>

Alternate installation
----------------------

Installing with a virtualenv/or with pip install –user
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if using virtualenv, first do a

.. raw:: html

   <pre>python -m venv $HOME/venvs/declad</pre>

and activate the environment.

.. raw:: html

   <pre>. $HOME/venvs/declad/bin/activate</pre>

if not using virutalenv, do ``pip install --user`` instead of just
``pip install``, below.

Then pip install the dependencies:
* webpie
* metacat
* rucio-clients
* py-jinja2

Declad itself isn’t currently pip-installable, you can clone it from
https://github.com/fermitools/declad.git and symlink the “declad”
subdirectory in your virtualenv or pip local “site_packages” directory.
