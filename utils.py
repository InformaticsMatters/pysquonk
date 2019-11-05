"""Utility functions for use with the Informatics Matters Squonk REST API.

"""

import gzip
import os
import datetime
import json
from uuid import uuid1
from logging import debug, error

# The version of this module.
# Modify with every change, complying with
# semantic 2.0.0 rules.
__version__ = '1.0.0'

def tobasic(file_name):
    """
    Converts a squonk org.squonk.types.MoleculeObject to 
    org.squonk.types.BasicObject
    Unzips the file first if it name ends in .gz

    Parameters
    ----------
    file_name: str
        name of the file. if it ends in gz is assumed to be gzipped

    Returns
    -------
    Returns a string containing the file data
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

    json_data = json.loads(file_data)
    new_json=[]
    count=0
    for mol in json_data:
        count+=1
        mol['source'] = mol['values']['SMI']
        del(mol['values'])
        new_json.append(mol)

    meta_data = {'type':'org.squonk.types.BasicObject','size':count}
    return (new_json, meta_data)

def mol2sdf(file_name):
    """
    Converts a mol format file to sdf by adding $$$$ onto the end.
    Unzips the file first if it name ends in .gz

    Parameters
    ----------
    file_name: str
        name of the file. if it ends in gz is assumed to be gzipped

    Returns
    -------
    Returns a string containing the file data
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

    file_data += "$$$$\n"
    return file_data

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
    lines=squonk_string
    if(isinstance(lines,str)):
        lines=squonk_string.splitlines()

    today = datetime.date.today()
    date_string = today.strftime("%d-%b-%Y %H:%M:%S UTC")

    # start of the output data
    mol_list = []
#   data='['

    # process each line in the file
    for line in lines:
#       debug('LINE:'+line)

        # start a new molecule def
        if in_mol:
            data = {}
            data['uuid'] = str(uuid1())
            mol_data = ''
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
            mol_data += line
            mol_data += "\n"

        # found the end of a molecule
        if line.startswith('M  END'):
            data['source'] = mol_data
            data['format'] ='mol'
            if type == 'sdf':
                in_opts=True
                values={}
            else:
                in_mol = True

        # found the end of options in sdf file
        if line.startswith('$$$$'):
            in_mol = True
            in_opts=False
#           debug('end of opts sdf')
            val_strings={}
            for name, value in values.items():
                 val_strings[name] = value
            data['values'] = val_strings
            mol_list.append(data)

    # end of the data

    meta_data={}
    # sdf meta data
    if type == 'sdf':
        size = mol_count
        meta_data['type'] = "org.squonk.types.MoleculeObject"
        meta_data['size'] = size
        val_strings={}
        for name in names.keys():
             type_str = 'java.lang.String'
             val_strings[name] = type_str
        meta_data['valueClassMappings'] = val_strings
        base_name = os.path.basename(file_name)
        metaprops = []
        for name in names.keys():
            metaprops.append(metaprop(name,date_string,base_name))
        meta_data['fieldMetaProps'] = metaprops
        properties = {}
        properties['created'] = date_string
        properties['source'] = 'SD file: ' + base_name 
        properties['description'] = 'Read from SD file: ' + base_name
        histories = []
        for name in names.keys():
            histories.append(history(name,date_string,file_name))
        properties['history'] = "\n" . join(histories)
        meta_data['properties'] = properties

    return (mol_list, meta_data, 0)

# format a fields metaproperty entry
def metaprop(field,date,filename):
    data = {}
    data['fieldName'] = field
    values = {}
    values['created'] = date
    values['source'] = 'SD file: ' + filename
    values['description'] = 'Data field from SDF'
    values['history'] = '[' + date + '] Value read from SD file property'
    data['values'] = values
    return data

# format a fields history entry
def history(field,date,filename):
    data = '[' + date + ']'
    data += ' Added field ' + field
    return data
