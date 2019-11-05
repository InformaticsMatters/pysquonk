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
import json
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
        if 'inputDescriptors' in job_json:
            self.inputs = job_json['inputDescriptors']
        if 'optionDescriptors' in job_json:
            self.options = job_json['optionDescriptors']

    # write out a template yaml file from the definition
    def template(self, yaml_name, format='squonk'):
        inputs = {'inputs' : self.default_inputs(format) }
        options = self.default_options()
        with open(yaml_name, 'w') as outfile:
            outfile.write("service_name: " + self._service + "\n")
            yaml.dump(inputs, outfile, default_flow_style=False)
            outfile.write("options:\n")
            for option in options:
                outfile.write(option + "\n")

    # get the file types expected for a given InputDescriptor from the 
    # service definition
    def _get_file_types(self,input):
            media_type = input['mediaType']
            if media_type in file_types:
                return file_types[media_type]
            else:
                raise Exception('SquonkJobDefinition unknown media type: ' + media_type)

    # create default files from the service definition
    def default_inputs(self,format='squonk'):
        data = {}
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
            data[input['name']] = input_data
        return data

    # defaults for the options
    def default_options(self):
        data = []
        for option in self.options:

            # set a default depending on type.

            type = option['typeDescriptor']['type']
            value = "'id'"
            if type == 'java.lang.Integer':
                value = "1"
            if type == 'java.lang.Float':
                value = "1.0"
            if type == 'java.lang.Boolean':
                value = "'false'"
            if type == 'org.squonk.types.NumberRange$Float':
                value = "'1.0|4.0'"
            if type == 'org.squonk.types.NumberRange$Integer':
                value = "'1|4'"

            # put service default value in if there is one.
            if 'defaultValue' in option:
                value = str(option['defaultValue'])

            # put the possible values in as a comment.
            if 'values' in option:
                val_string = ", " . join(option['values'])
                value = value + " # " + val_string

            # compose yaml

            key = option['key']
            yaml_line = "  " + key + ": " + value

            # comment out the value if there is a default

            min=0
            if 'minValues' in option:
                min = option['minValues']
            if 'defaultValue' in option and min==0:
                yaml_line = '#' + yaml_line[1:]
            data.append(yaml_line)

        return data

    # get the files data to create a job
    def get_job_files(self,inputs):
        files=[]
        for input in self.inputs:
            # some inputs may not be present eg in core.dataset.merger.v1
            name = input['name']
            if not name in inputs:
                continue
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
            logging.debug('validate:'+key)
            min = 0
            if 'minValues' in option_json:
                min = option_json['minValues']
            expected_options[key] = option_json
            if not 'defaultValue' in option_json and min>0:
                if not key in options:
                    print("ERROR: missing job option: " + key)
                    return False
        # loop round the options we actualy have and if expected
        # check have correct number of values and types.
        for key in options:
            if key in expected_options:
                options_json = expected_options[key]
                type_ = options_json['typeDescriptor']['type']
                max = 1
                if 'maxValues' in option_json:
                    max = option_json['maxValues']
                if not self.correct_type(options[key],type_):
                    logging.error("option {} is of wrong type. shoud be {}:".format(key,type_))
                    return False

        # loop round the expected input files (json) and
        # check they exist

        expected_inputs = {}
        for input_json in self.inputs:
            name = input_json['name']
            expected_inputs[name] = input_json
            if not name in inputs:
                print("WARNING: missing input file: " + name)
            # downgraded to a warning because some services don't need all
            # inputs, eg core.dataset.enricher.v1.yaml
            #   return False

        # check that we either have 'data' and 'metadata' keywords or
        # 'sdf' or 'mol'

        for input in expected_inputs:
            input_json = expected_inputs[input]
            file_types = self._get_file_types(input_json)
            if input in inputs:
                if not 'data' in inputs[input] and not 'sdf' in inputs[input] and not 'mol' in inputs[input]:
                    print("ERROR: no data: keyword for input file: " + name)
                    return False
                if 'meta' in file_types:
                    if not 'sdf' in inputs[input] and not 'mol' in inputs[input]:
                        if not 'meta' in inputs[input]:
                            print("ERROR: no meta: keyword for input file: " + name)
                            return False
        return True

    # check option value of correct type.
    def correct_type(self,value,type):
        if type=='java.lang.Integer':
            if isinstance(value, int):
                return True
        if type=='java.lang.Float':
            if isinstance(value, float):
                return True
        if type=='java.lang.Boolean':
            if isinstance(value, bool):
                return True
        if type=='java.lang.String':
            if isinstance(value, str):
                return True
#       Range check is commented out because some jobs don't follow this format.
        if type == 'org.squonk.types.NumberRange$Integer':
#           return _range(value, int)
            return True
        if type == 'org.squonk.types.NumberRange$Float':
#           return _range(value, float)
            return True

        return False

# verify a range parameter is 2 values seperated by pipe 1.0|1.0
def _range(value,type_):
    vals = value.split('|')
    if len(vals) != 2:
        return False
    if not isinstance(vals[0], type):
        return False
    if not isinstance(vals[1], type):
        return False
    
    return True
