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
import logging
from requests_toolbelt.multipart import decoder
from email.parser import BytesParser, Parser
from email.policy import default
from .SquonkJobDefinition import SquonkJobDefinition

class SquonkJob:

    def __init__(self, server, service=None, options={}, inputs={}, yaml=None, end_point='jobs/'):
        self._server = server
        self._service = service
        self._inputs = inputs
        self._options = options
        self._yaml = yaml
        self._end_point = end_point
        self._job_id = None

    def initialise(self,service_info):
        # if there is yaml read it, loading in:
        if self._yaml:
            job_yaml = yaml.load(open(self._yaml))
            for section in ['service_name','options','inputs']:
                if not section in job_yaml:
                    print("ERROR: " + self._yaml + " missing section: " + section)
                    return False
            self._service = job_yaml['service_name']
            self._options = job_yaml['options']
            self._inputs = job_yaml['inputs']
   
        # check we have some files or options
        if len(self._inputs)==0 and len(self._options)==0:
            print("ERROR: " + self._yaml + " missing section: " + section)
            return False

        # check service name in yaml or passed in.
        if not self._service:
            print("ERROR: service not defined in config or passed in")
            return False

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
        self.validate()
        files = self.job_def.get_job_files(self._inputs)
        logging.debug(files)
        data_opt_str = '{}'.format(self._options)
        data_opt_str = data_opt_str.replace("'", '"')
        form_data = { 'options': data_opt_str }
        for file in files:
           key = file['name'] + '_data'
           form_data[key] = ( key, open(file['data'], 'rb'), file['type'])
           if 'meta_data' in file:
               key = file['name'] + '_metadata'
               form_data[key] = ( key, open(file['meta_data'], 'rb'), file['meta_type'])
        response = self._server.send('post', self._end_point + self._service, form_data)
        if response:
            job_status = response.json()
            self._job_id = job_status['jobId']
            logging.debug("Job Status: " + str(job_status) + " JobID: " + self._job_id)
            return self._job_id
        else:
            return response

# get a jobs status
    def get_status(self,job_id):
        response = self._server.send('get', self._end_point + job+id + '/status')
        if response:
            job_json = response.json()
            status = job_json['status']
            return status
        else:
            return response
