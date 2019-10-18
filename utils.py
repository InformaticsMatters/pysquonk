"""Utility functions for use with the Informatics Matters Squonk REST API.

"""

import gzip
import os
import datetime
from uuid import uuid1
from logging import debug, error

# The version of this module.
# Modify with every change, complying with
# semantic 2.0.0 rules.
__version__ = '1.0.0'

def tosquonk(file_name,type=None):
    """
    Converts a mol or sdf format file to squonk data and meta data files.
    Unzips the file first if it name ends in .gz

    Parameters
    ----------
    file_name: str
        name of the file. if it ends in gz is assumed to be gzipped
    type: str
        type of file 'mol' or 'sdf'. If not specified determines it from 
        the file name.

    Returns
    -------
    Returns a tuple containing two strings, and a return code.
       -the data
       -the meta data
       -return code

    """
    file_data = ''
    file_base, file_ext = os.path.splitext(file_name)
    if file_ext == '.gz':
        file_base, file_ext = os.path.splitext(file_base)
        debug('opening gzipped file:' + file_name)
        with gzip.open(file_name, 'rt') as f:
            file_data = f.read()
    else:
        debug('opening ordinary file:' + file_name)
        with open(file_name, 'r') as f:
            file_data = f.read()

    if not type:
        type = file_ext[1:]
        
    if type == 'mol':
        return str2squonk(file_data, 'mol', file_name)
    else:
        if type == 'sdf':
            return str2squonk(file_data, 'sdf', file_name)
        else:
            error('File: ' + file_name + ' is of wrong type ' + type)
            return(' ', ' ', 1)

def str2squonk(squonk_string, type, file_name):
    """
    Converts a mol format file as a string to squonk data and meta data files

    Parameters
    ----------
    squonk_string: str
        data from the mol file.

    Returns
    -------
    Returns a tuple containing two strings:
       -the data
       -the meta data
       -return code

    """
  
    debug('converting file of type: ' + type)
    mol_count=0
    in_mol=True
    in_opts=False
    got_name=False
    names={}
    values={}
    head_string='{"uuid":"' + str(uuid1()) + '","source":"'
    mol_end='"'
    format_string=', "format":"mol"'
    opt_start=', "options":"{'
    opt_end='}"'
    tail_string='}'
    lines=squonk_string
    if(isinstance(lines,str)):
        lines=squonk_string.splitlines()

    today = datetime.date.today()
    date_string = today.strftime("%d-%b-%Y %H:%M:%S UTC")

    # start of the output data
    data='['

    # process each line in the file
    for line in lines:
#       debug('LINE:'+line)

        # start a new molecule def
        if in_mol:
            data += head_string
            in_mol = False
            mol_count+=1

        # processing options
        if in_opts:
            if got_name:
                values[name] = line.rstrip()
                got_name = False
            if line.startswith('> <'):
                end_name=line[3:].find('>')
                if end_name == -1:
                    error('Invalid SDF file format')
                else:
                    got_name = True
                    name = line[3:end_name+3]
                    names[name] = 1
        else:
            data += line
# TODO issue with end of line ??
            data += "\n"

        # found the end of a molecule
        if line.startswith('M  END'):
            data += mol_end
            data += format_string
            if type == 'sdf':
                debug('in_opts sdf')
                in_opts=True
                values={}
            else:
                in_mol = True
                data += tail_string

        # found the end of options in sdf file
        if line.startswith('$$$$'):
            in_mol = True
            in_opts=False
#           debug('end of opts sdf')
            data += opt_start
            val_strings=[]
            for name, value in values.items():
                 val_strings.append('"' + name + '":"' + value + '"')
            data += ",".join(val_strings)
            data += opt_end
            data += tail_string

    # end of the data
    data+=']'

    meta_data=''
    # sdf meta data
    if type == 'sdf':
        size = mol_count
        meta_data = '{"type":"org.squonk.types.MoleculeObject","size":'
        meta_data += str(size)
        meta_data += ',"valueClassMappings":{'
        val_strings=[]
        for name in names.keys():
             type_str = 'java.lang.String'
             val_strings.append('"' + name + '":"' + type_str + '"')
        meta_data += ",".join(val_strings)
        meta_data += '},"fieldMetaProps":['
        for name in names.keys():
            meta_data += metaprop(name,date_string,file_name)
        meta_data += '], properties : {"created":"' + date_string
        meta_data += '","source":"SD file: ' + file_name 
        meta_data += '"","description":"Read from SD file: ' + file_name
        meta_data += '","history":"'
        for name in names.keys():
            meta_data += history(name,date_string,file_name)
        meta_data += '"}}'

    return (data, meta_data, 0)

# format a fields metaproperty entry
def metaprop(field,date,filename):
    data = '{"fieldName":"' + field + '","values":{"created":"'
    data += date
    data += '","source":"SD file: ' + filename + '"'
    data += ',"description":"Data field from SDF","history":"['
    data += date
    data += ' Value read from SD file property"}}'
    return data

# format a fields history entry
def history(field,date,filename):
    data = '[' + date + ']'
    data += ' Added field ' + field + '\n'
    return data
