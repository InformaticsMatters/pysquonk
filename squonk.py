#! /usr/bin/env python
"""A Python wrapper around the Informatics Matters Squonk REST API.

Workflow is to create a Squonk instance from either a config file or
parameters passed in and then run a job. See example program below:

    from squonk import Squonk

    config = {
     'base_url' : 'https://jobexecutor.apps.xchem.diamond.ac.uk/jobexecutor/rest/v1',
     'auth_url' : 'https://sso.apps.xchem.diamond.ac.uk/auth/realms/xchem/protocol/openid-connect/token',
     'username' : 'joblogs',
     'password' : '123456',
     'services_endpoint' : 'services/',
     'jobs_endpoint' : 'jobs/'
    }

    # create squonk object from config
    squonk = Squonk(config=config)

    # save yaml template
    # TODO - option to pass in sdf type, as opposed to data/meta
    squonk.job_yaml_template('slice_template.yaml', 'core.dataset.filter.slice.v1')

    # job with inputs from parameters

    options = {"skip":2,"count":3}
    inputs = { 'input': {
                'data' : '../data/testfiles/Kinase_inhibs.json.gz',
                'meta' : '../data/testfiles/Kinase_inhibs.metadata' }
        }
    service = 'core.dataset.filter.slice.v1'
    job = squonk.create_job(service, options, inputs)

    # start job
    job_id = job.start()
    squonk.job_wait(job_id)
    squonk.job_delete(job_id)
"""

import configparser
import json
import logging
import time
import sys
from requests_toolbelt.multipart import decoder
from .SquonkAuth import SquonkAuth
from .SquonkServer import SquonkServer
from .SquonkJobDefinition import SquonkJobDefinition
from .SquonkJob import SquonkJob

# The version of this module.
# Modify with every change, complying with
# semantic 2.0.0 rules.
__version__ = '1.0.0'

# how content-types that are part of the job results response 
# are to be processed.
output_content_types = {
   'chemical/x-mdl-sdfile': 'write_file',
   'application/x-squonk-dataset-molecule+json': 'write_file',
   'application/x-squonk-dataset-basic+json': 'write_file',
   'application/x-squonk-molecule-object+json': 'write_file',
   'image/png': 'write_file',
   'chemical/x-mol2': 'write_file'}

class Squonk:

    def __init__(self,config_file='config.ini', config=None):
        """
        Instantiate a Squonk object.

        Create a Squonk object for running the Squonk Python API.
        Pass in configuration information such as urls , end points
        and username and password. Can be supplied via a config_file
        or a dictionary passed as an input parameter.
        If config is specified, then that is uses otherwise it attempts
        to read config_file.

        Parameters
        ----------
        config_file : str
            Name of the configuration file. defaults to config.ini
        arg2 : dict
            Configuration information

        Returns
        -------
        int
            Description of return value

        """

        # TODO - should we look for config in ENV variable DIR ?
        # if config is passed in then use that
        if config:
            self._config = config
        # otherwise read the config file
        else:
            self._config = {}
            settings = configparser.ConfigParser()
            settings._interpolation = configparser.ExtendedInterpolation()
            settings.read(config_file)

            self._config['client_id'] = settings.get('token', 'client_id')
        # TODO - change ini file format ? eg to yaml
        # TODO client secret
        # self.token_client_secret = settings.get('token', 'client_secret')
            self._config['username'] = settings.get('token', 'username')
            self._config['password'] = settings.get('token', 'password')
            self._config['auth_url'] = settings.get('token', 'url')
            self._config['base_url'] = settings.get('general', 'base_url')
            self._config['services_endpoint'] = settings.get('ids', 'endpoint')
            self._config['jobs_endpoint'] = settings.get('job', 'endpoint')

        logging.debug(json.dumps(self._config))
        # Validate the config
        for section in ['auth_url', 'base_url', 'services_endpoint', 'jobs_endpoint']:
            if not section in self._config:
                raise Exception(section + ' missing from config')
        if not 'client_secret' in self._config:
            for section in ['username', 'password']:
                if not section in self._config:
                    raise Exception(section + ' missing from config')

        # Create a SquonkAuth object
        # then authenticate (checking for success)...
        sa = SquonkAuth(self._config['auth_url'], self._config['username'], self._config['password'])
        sa.authenticate()

        # create SquonkServer object
        self.server = SquonkServer(sa, self._config['base_url'])

    def list_services(self):
        """
        Returns all the available service definitions

        Parameters
        ----------

        Returns
        -------
        json
            Json for all the available services

        """

        response = self.server.send('get', self._config['services_endpoint'])
        if response:
            return response.json()
        else:
            print("ERROR: failed to get list of services")
            return []

    def list_service_ids(self):
        """
        Returns a list of all the service ids

        Parameters
        ----------

        Returns
        -------
        []str
            List of all the service ids

        """

        response = self.list_services()
        if response:
            out = [method['id'] for method in response]
            return out
        else:
            return response

    def list_service_info(self, service_id):
        """
        Returns the service name and description.

        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1

        Returns
        -------
        dict
            Dictionary containing service id, name and description

        """

        response = self.list_services()
        if response:
            out = [method for method in response if method['id'] == service_id]
            return out
        else:
            response

    def list_full_service_info(self, service_id):
        """
        Returns the service name and description.

        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1

        Returns
        -------
        dict
            Dictionary containing service id, name and description

        """

        response = self.server.send('get', self._config['services_endpoint'] + '/' + service_id)
        if response:
            return response.json()
        else:
            return {}

    def list_service_info_field(self, service_id, field):
        """
        Returns a specified field from the service info

        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1

        Returns
        -------
        str
            Field from the service info.

        """

        response = self.list_full_service_info(service_id)
        if field in response:
            field = response[field]

            return field
        else:
            return ''

    def job_yaml_template(self, filename, service):
        """
        Outputs a yaml template for a specified service.

        Values for the options will be output as 1, 1.0, or 'id' depending
        on if the expected type is integer, float or string.

        Parameters
        ----------
        filename : str
            Name of the file to write to
        service : str
            Name of the service eg core.dataset.filter.slice.v1

        """
        job_def = SquonkJobDefinition(service)
        info = self.list_full_service_info(service)
        response = job_def.get_definition(info)
        if response:
            job_def.template(filename)
        return response
# 
# TODO - don't send job class back, combine it with:
#            run()
#            options 2 yaml
#            yaml 2 options
#
    def create_job(self, service=None, options={}, inputs=[], yaml=None):
        """
        Create a Squonk job

        The input options for the job can be defined either by parameters
        passed into the function or read from a yaml file. If the yaml
        file is specified then it will be used in preference. The yaml file
        or values supplied via parameters are validated against the service
        definition which is retreived from the server.

        Parameters
        ----------
        service : str
            Name of the service eg core.dataset.filter.slice.v1
        options : dict
            The jobs options in the form of a dictionary
        inputs : dict
            The jobs file inputs in the form of a dictionary
        yaml : str
            A yaml file defining the job. A template file cna be generated
            using the function job_yaml_template

        Returns
        -------
        SquonkJob
            A squonk job object which can be used to run the job.

        """

        job = SquonkJob(self.server,service=service, options=options, inputs=inputs, yaml=yaml, end_point= self._config['jobs_endpoint'])
        info = self.list_full_service_info(service)
        job.initialise(info)
        return job

    # get your jobs
    def list_jobs(self):
        """
        List all the job ids for jobs owned by the user.

        Parameters

        Returns
        -------
        []str
            List of job ids of jobs for the current user

        """

        jobs=[]
        response = self.server.send('get', self._config['jobs_endpoint'])
        if response:
            job_json = response.json()
            for job in job_json:
                job_id = job['jobId']
                logging.debug(job_id)
                jobs.append(job_id)
        return jobs

    # delete a job
    def job_delete(self, job_id):
        """
        Delete the specified job

        Parameters
        ----------
        job_id : str
            Id of the job to be deleted

        Returns
        -------
        response
            response from the srevice. This can be used for failure checking
            eg by coding:
            if response:

        """

        logging.debug('Deleting job ' + job_id)
        response = self.server.send('delete', self._config['jobs_endpoint'] + job_id)
        return response

    # delete all my jobs
    def job_delete_all(self):
        """
        Delete all jobs for the current user

        Parameters
        ----------

        Returns
        -------

        """

        jobs = self.list_jobs()
        for id in jobs:
            self.job_delete(id)

    # get a jobs status
    def job_status(self,job_id):
        """
        Get the status of a job from its job_id

        The possible job statuses are:
            PENDING
            SUBMITTING
            RUNNING
            RESULTS_READY
            COMPLETED
            ERROR
            CANCELLED

        Parameters
        ----------
        job_id : str
            The id of the job.

        Returns
        -------
        str
            The job status eg RUNNING or RESULTS_READY or SQUOANK_API_ERROR if
            there was some error trying to obtain the job status

    """

        status = 'SQUOANK_API_ERROR'
        response = self.server.send('get', self._config['jobs_endpoint'] + job_id + '/status')
        if response:
            job_json = response.json()
            status = job_json['status']
            return status

# wait for job to finish then get the results
    def job_wait(self, job_id, dir=None, sleep=10, delete=True):
        """
        Waits for the specified job to finish and if it reaches a status of
        RESULTS_READY then reteives the jobs results.

        File created from the job are saved to the current directory or
        the specified direectory

        Parameters
        ----------
        job_id : str
            Description of arg1
        dir : str
            Optional directory to save the job output to.
        sleep : int
            Time in seconds to sleep for before checking results again.
            Default is 10.
        delete: boolean
            True to delete the job after getting the results back successfully
            or False to keep the job (optional: default is True)

        Returns
        -------

        """
        status = 'RUNNING'
        while status=='RUNNING':
            status = self.job_status(job_id)
            print(status)
            time.sleep(sleep)
        if status == 'RESULTS_READY':
            self.job_results(job_id, dir)
            if delete:
                self.job_delete(job_id)
        else:
            print('Job Failed status='+status)

    def _get_content_type(self,header):
        content_type = header['Content-Type'.encode()].decode()
        return content_type

    def _get_filename(self,header):
        filename=''
        content_disp = header['Content-Disposition'.encode()].decode()
        indx = content_disp.find('filename=')
        if indx!= -1:
            filenstr=content_disp[indx:]
            indx = filenstr.find('=')
            if indx!= -1:
                filename=filenstr[indx+1:]
        return filename

    # get jobs results
    def job_results(self,job_id,dir=None):
        """
        Get the results of the given job

        This will write out the returned files to the current directory
        or the specified directory

        Parameters
        ----------
        job_id : str
            Id of the job 
        dir : str
            Optional directory. Defaults to the current directory if not
            supplied.

        Returns
        -------
        response
            The reponse object from the service call

        """

        response = self.server.send('get', self._config['jobs_endpoint'] + job_id + '/results')
        if not response:
            return response
        logging.debug('parsing response ....')
        count=0
        multipart_data = decoder.MultipartDecoder.from_response(response)
        for part in multipart_data.parts:
            count+=1
            logging.debug("HEADER =========PART:"+str(count))
            logging.debug(part.headers)
# TODO perhaps we should just look at any file attachments and save them?
            content_type = self._get_content_type(part.headers)
            if content_type in output_content_types:
                logging.debug("PROCESSING " + content_type)
                self._write_file(part,dir)
            else:
                logging.debug("IGNORED " + content_type)
#               logging.debug("PART ======= CONTENT =========")
#               logging.debug(part.content)
        return response

    def _write_file(self,part,dir):
        file_name = self._get_filename(part.headers)
        if dir:
            file_name = dir + '/' + file_name
        logging.debug(file_name)
        content = part.content.decode()
        content_json=json.loads(content)
        file_data=content_json[0]['source']
        with open(file_name, 'w') as f:
            f.write(file_data)
            f.close()

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

# TODO help option, type for yaml template generation

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    # Create a Squonk object
    squonk = Squonk()

    # Get command line
    input = sys.argv[1]

    # its a .yaml file, then run the job
    if input.endswith('.yaml'):
        print('Input: ' + input + ' assuming job yaml file, running job')
        job = squonk.create_job(yaml=input)
        job_id = job.start()
        print('submitted job: ' + job_id)
        # wait for job to finish and get the results
        squonk.job_wait(job_id)

    # Otherwise assume its a service name and write a yaml template
    else:
        print('Input: ' + input + ' assuming service name')
        squonk.job_yaml_template(input+'.yaml', input)
