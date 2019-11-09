#! /usr/bin/env python
"""Python script to guess what a file is and write some information about it

   usage: guess_file.py <in_file> <field>
 
   reads <in_file> and tries to guess if its a squonk dataset, metdata, mol
   or sdf file. Writes out the time when the file was last modified, the
   number of records and the values from the first record.  
   <field> is optional, but if specified writes out a count of all values of
   the specified field for all records in the file.

"""

import argparse
import json
import logging
import sys
import os
import time
from utils import peek

file_name = sys.argv[1]
field=None
if len(sys.argv)>2:
    field = sys.argv[2]

mtime=time.ctime(os.path.getmtime(file_name))
print('File modification time='+str(mtime))

file_info = peek(file_name,True,field)
print(file_info)
