"""A SquonkJobDefinition represents the service definition of a job
   (whereas SquonkJob is a particular instance ie set of options, 
    input files and a job_id )

   This includes a client side representation of the service definition.
   The class includes methods to get a service definition, validate a 
   jobs input parameters against it and write a template yaml file.

"""

import configparser
import logging
import shutil, os
import requests
# import curlify
import json
# from functions import check_response
import yaml
from requests_toolbelt.multipart import decoder
from email.parser import BytesParser, Parser
from email.policy import default

# Mappings from the input descriptions to what the type passed to the job
# service should be.
file_types = {'application/x-squonk-dataset-basic+json' :
                {'data' : {'mime': 'application/x-squonk-basic-object+json',
                           'type': '?' },
                 'meta' : {'mime': 'application/x-squonk-dataset-metadata+json',
                           'type': '?' } },
              'application/x-squonk-dataset-molecule+json' :
                {'data' : {'mime': 'application/x-squonk-molecule-object+json',
                           'type': '?'},
                 'meta' : {'mime': 'application/x-squonk-dataset-metadata+json',
                           'type': '?'} },
              'application/zip' :
                {'data' : {'mime': 'application/zip',
                           'type': 'zip'} },
              'chemical/x-pdb' : 
                {'data' : {'mime': 'application/x-squonk-molecule-object+json',
                           'type': 'pdb'} }
             }

class SquonkJobDefinition:
    def __init__(self, service):
        self._service = service
        self.inputs = []
        self.options = []

    # set job definition from service info 
    def get_definition(self,job_json):
        self.inputs = job_json['inputDescriptors']
        self.options = job_json['optionDescriptors']

    # write out a template yaml file from the definition
    def template(self, yaml_name, format='squonk'):
        data = self.defaults(format)
        with open(yaml_name, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

    # get the file types expected for a given InputDescriptor from the 
    # service definition
    def _get_file_types(self,input):
            media_type = input['mediaType']
            if media_type in file_types:
                return file_types[media_type]
            else:
                raise Exception('SquonkJobDefinition unknown media type: ' + media_type)

    # create default options and files from the service definition
    def defaults(self,format='squonk'):
        data = { 'service_name' : self._service,
                 'inputs' : {},
                 'options' : {} }
        file_type_key = format
        if format== 'squonk':
            file_type_key = 'data'
        
        # defaults for the input files
        for input in self.inputs:
            file_types = self._get_file_types(input)
            input_data = { file_type_key : 'data_file' }
            if format == 'squonk':
                if 'meta' in file_types:
                    input_data['meta'] = 'meta_data_file'
            data['inputs'][input['name']] = input_data

        # defaults for the options
        for option in self.options:
            type = option['typeDescriptor']['type']
            key = option['key']
            value = 'id'
            if type == 'java.lang.Integer':
                value = 1
            if type == 'java.lang.Float':
                value = 1.0
            data['options'][key] = value
        return data

# get the files data to create a job
    def get_job_files(self,inputs):
        files=[]
        for input in self.inputs:
            name = input['name']
            input_value = inputs[name]
            format = 'error'
            if 'data' in input_value:
                format = 'data'
            if 'mol' in input_value:
                format = 'mol'
            if 'sdf' in input_value:
                format = 'sdf'
            if format == 'error':
                logging.error('File type should be data, sdf or mol in:'+str(input_value))
                return false
            
            file_types = self._get_file_types(input)
            file = { 'name' : name,
                     'format' : format,
                     'data' : input_value[format],
                     'type' : file_types['data']['mime'] }
            if 'meta' in file_types:
                if format == 'data':
                    if not 'meta' in input_value:
                        logging.error('Missing meta keyword in:'+str(input_value))
                        return False
                    file['meta_data'] = input_value['meta']
                file['meta_type'] = file_types['meta']['mime']
            files.append(file)
        return files

# validate the job inputs against the service definition
    def validate(self,options,inputs):
        expected_options = {}
        # loop round the expected options (json) and
        # check they exist - presumably can be left out if default value?
        for option_json in self.options:
            key = option_json['key']
            min = option_json['minValues']
            expected_options[key] = option_json
            if not 'default_value' in option_json and min>0:
                if not key in options:
                    print("ERROR: missing job option: " + key)
                    return False
        # loop round the options we actualy have and if expected
        # check have correct number of values and types.
        for key in options:
            if key in expected_options:
                options_json = expected_options[key]
                type = option_json['typeDescriptor']['type']
                max = option_json['maxValues']
                if self.correct_type(options[key],type):
                    return False

        # loop round the expected input files (json) and
        # check they exist
        expected_inputs = {}
        for input_json in self.inputs:
            name = input_json['name']
            expected_inputs[name] = input_json
            if not name in inputs:
                print("ERROR: missing input file: " + name)
                return False
        for input in expected_inputs:
            input_json = expected_inputs[name]
            if not 'data' in input:
                print("ERROR: no data: keyword for input file: " + name)
                return False
            file_types = self._get_file_types(input_json)
            if 'meta' in file_types:
                if not 'meta' in input:
                    print("ERROR: no meta: keyword for input file: " + name)
                    return False

# check option value of correct type.
    def correct_type(self,value,type):
        if type=='java.lang.Integer':
            if isinstance(value, int):
                return True
#           try: 
#               int(value)
#               return True
#           except ValueError:
#               return False
        if type=='java.lang.Float':
            if isinstance(value, int):
                return True
#           try: 
#               float(value)
#               return True
#           except ValueError:
#               return False
        if type=='java.lang.String':
            if isinstance(value, int):
                return True

        return False
