Using Declad
============

Once Declad has been configured to monitor a dropbox, to use Declad, all
you need to do is place files, along with matching metadata files (but
see :doc:`Metadata Extractors`), in the dropbox directory. It will
periodically scan the dropbox directory, transfer files to their
configured destination, and declare them to the configured data
management systems.

Declad also has a monitoring web interface, which if you have enabled it
in your configuration, lets you check on the status of the service,
browse the dropbox, and view the history of transferred files, etc.

Metadata Files
--------------

Although Declad will declare files to both SAM and Metacat/Rucio, it
currently expects metadata files to be:

* named filename.json for a given filename
* valid JSON format
* in either SAM’s metadata format, or Metacat’s
* currently requires at least the following fields by default (list is now configurable):

  * file_size
  * checksum
  * runs
