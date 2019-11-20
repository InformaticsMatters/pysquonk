# pysquonk
PySquonk
========

Pysquonk is a python API wrapper round the Informatics Matters Squonk Rest
 Services. It can be used to submit jobs, check their status and retreive
the jobs results. It can be used in two ways:
- from the command line
- writing python scripts using the API


Installation
------------

From github https://github.com/InformaticsMatters/pysquonk

From pip:
  pip install im-pysquonk

(note if you install from pip you get a script so you can also just run from the command line using the command pysquonk without specifiying the full path)

Running from the command line
-----------------------------

Copy the file config.ini from github and save it into the directory you are going to run the command from. Edit your username and password into the file, or
pass them via the command line (see below). The job to run is specified using
yaml files. Examples of yaml files for various jobs are available in the yaml
directory. For example, if you installed with pip, the command;

  pysquonk -r yaml/pipelines.rdkit.sucos.o3da.yaml -o outdir

will run the job defined by the file pipelines.rdkit.sucos.o3da.yaml and write its output to the directory outdir. To get help run.

  pysquonk -h

If you did not install pysquonk via pip, but you have a directory SQUONKDIR containing the contents of the repository then the command would be:

  python SQUONKDIR/squonk -h

If you want to run a job that does not have an example in the yaml directory,
then the command:

  pysquonk -s pipelines.rdkit.sucos.o3da -o outdir

will write out an example yaml file to directory outdir. You can then amend this as required.

Using the Python API
--------------------

The API documentation is in [doc/squonk.md](doc/squonk.md). There are some examples of usage there and also there is an example program in test_harness.py.
There is also a Jupyter notebook which shows how to use the API.


Development and Testing
-----------------------

To run all the test jobs in the yaml sub directory, from the top level of the repo run:

  python test_jobs.py

(will prompt for username and password). -r option will run one of the jobs.

To run the script that executes the API functions:

  python test_harness.py
(will prompt for username and password).

To upload a new version to pip:
 - update the version number in setup.py
 - rm dist/*
 - python setup.py bdist_wheel
 - twine upload dist/*
