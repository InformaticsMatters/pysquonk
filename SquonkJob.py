"""A SquonkJob is a particular instance of a SquonkJobDefinition
   ie set of options, input files and a job_id.
   (A SquonkJobDefinition represents the service definition of a job)

   This includes methods to create start a job from either passed in    
   parameters or input yaml file. 

"""
import configparser
import shutil, os
import requests
# import curlify
# import auth
import json
import yaml
import logging as log
from requests_toolbelt.multipart import decoder
from email.parser import BytesParser, Parser
from email.policy import default
try:
    from .SquonkJobDefinition import SquonkJobDefinition
    from .utils import tosquonk
except:
    from SquonkJobDefinition import SquonkJobDefinition
    from utils import tosquonk

class SquonkJob:

    def __init__(self, server, service=None, options={}, inputs={}, yaml=None, end_point='jobs/'):
        self._server = server
        self._service = service
        self._inputs = inputs
        self._options = options
        self._yaml = yaml
        self._end_point = end_point
        self._job_id = None

    def check_input(self):
        # if there is yaml read it, loading in:
        if self._yaml:
            job_yaml = yaml.load(open(self._yaml))

            # check the yaml file contains the sections we expect
            for section in ['service_name','options','inputs']:
                if not section in job_yaml:
                    log.error("ERROR: " + self._yaml + " missing section: " + section)
                    return False
            self._service = job_yaml['service_name']
            self._options = job_yaml['options']
            self._inputs = job_yaml['inputs']
   
        # check we have some files or options
        if len(self._inputs)==0 and len(self._options)==0:
            log.error("ERROR: " + self._yaml + " has no inputs or options section")
            return False

        # check the input files exist
        for name, input_files in self._inputs.items():
            for file_key, file_name in input_files.items():
                if not os.path.isfile(file_name):
                    log.error("{} {} {} file does not exist".format(name, file_key, file_name))
                    return False

        # check service name in yaml or passed in.
        if not self._service:
            log.error("ERROR: service not defined in config or passed in")
            return False

        log.debug('SquonkJob: service:' + self._service)
        log.debug('SquonkJob: inputs:' + str(self._inputs))
        log.debug('SquonkJob: options:' + str(self._options))
        return True

    def get_service(self):
        return self._service

    def initialise(self,service_info):
        # get the service definition
        self.job_def = SquonkJobDefinition(self._service)
        response = self.job_def.get_definition(service_info)
        return response

# write out a yaml file from the job inputs
# TODO - file content is in strange order
    def write_yaml(self, yaml_name):
        data = { 'service_name' : self._service,
                 'input_data' : self._inputs,
                 'options' : self._options }
        with open(yaml_name, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

# validate the job inputs against the service definition
    def validate(self):
        self.job_def.validate(self._options, self._inputs)

# run the job 
    def start(self):
        """
        Submit the job to the server

        Parameters
        ----------

        Returns
        -------
        str
            string containing the job id.

        """

        # validate the job input options against the service definition
        self.validate()

        # get the input files

        files = self.job_def.get_job_files(self._inputs)
        if not files:
            return False
        log.debug(files)

        # format the options form data

        data_opt_str = '{}'.format(self._options)
        data_opt_str = data_opt_str.replace("'", '"')
        form_data = { 'options': data_opt_str }

        # for each file, send a tuple consisting of:
        #  name, data (file object or string), mime type

        for file in files:
           format = file['format']
           key = file['name'] + '_data'

           # If we have squonk format files then open them.

           if format == 'data':
               form_data[key] = ( key, open(file['data'], 'rb'), file['type'])
               if 'meta_data' in file:
                   key = file['name'] + '_metadata'
                   form_data[key] = ( key, open(file['meta_data'], 'rb'), file['meta_type'])

           # otherwise we have mol or sdf so convert them to strings.

           else:
               file_data, file_meta, rcode = tosquonk(file['data'], format)
               if rcode == 0:
                   form_data[key] = ( key, file_data, file['type'])
                   if 'meta_data' in file:
                       key = file['name'] + '_metadata'
                       form_data[key] = ( key, file_meta, file['type'])
               else:
                   return False

        # send the request
        log.debug(form_data)
        response = self._server.send('post', self._end_point + self._service, form_data)

        # if it worked, then get the job id

        if response:
            job_status = response.json()
            self._job_id = job_status['jobId']
            log.debug("Job Status: " + str(job_status) + " JobID: " + self._job_id)
            return self._job_id
        else:
            return response
