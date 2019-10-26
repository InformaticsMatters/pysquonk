#! /usr/bin/env python
"""Python script to convert mol or sdf files to squonk.

   usage: mol2squonk.py <in_file> <out_base>
 
   reads <in_file> and writes <out_base>.data and <out_base>.metadata

"""

import argparse
import json
import logging
import sys
import os
from utils import tosquonk

file_name = sys.argv[1]
out_name = sys.argv[2]

data, meta, rcode = tosquonk(file_name, 'mol')

if rcode != 0:
    print("Error converting")
else:
    f=open(out_name + '.data', 'w+')
    f.write(json.dumps(data))
    f.close()
    if meta:
        f=open(out_name + '.metadata', 'w+')
        f.write(json.dumps(meta))
        f.close()
