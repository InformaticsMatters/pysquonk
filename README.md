# pysquonk

The API documentation is in doc/squonk.md

Running from the command line is also possible, for options run:

  python squonk.py -h

The examples can be run using a command like:

  python squonk.py -r yaml/pipelines.rdkit.sucos.o3da.yaml -d -o outdir

from the pysquonk directory, where outdir is the directory where the job output
should go. This assumes that config.ini has been editted with your username 
and password (or you can pass username and password as command line options)

To run all the test jobs in the yaml sub directory:

  python test_jobs.py

(will prompt for username and password). -r option will run one of the jobs.

To run the script that executes the API functions:

  python test_harness.py
(will prompt for username and password).
