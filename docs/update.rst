Updating Declad
===============

When updating Declad to a new version with Spack, there are two updates
to do:

* Updating the recipe repository for the new version
* Installing the binary package

Updating the recipe repository
------------------------------

To do this we do a git pull in the scd_recipes area to get the latest
recipes

.. code-block:: shell

   $ spack repo list 
   $ cd <directory for scd_recipes, above>
   $ git pull

Installing new binary package
-----------------------------

This is the usual spack buildcache list and spack install –cache-only.

.. code-block:: shell

   $ spack buildcache list -al declad
   $ spack install --cache-only <hash from above> 
