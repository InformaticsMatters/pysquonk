#! /usr/bin/env python
"""A Python wrapper around the Informatics Matters Squonk REST API.

pysquonk.py can just be run as a main program. To see the help run:  
  pysquonk/squonk.py -h

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

    # save yaml template for squonk format (others are sdf and mol)
    squonk.job_yaml_template('slice_template.yaml', 'core.dataset.filter.slice.v1', 'squonk')

    # job with inputs from parameters

    options = {"skip":2,"count":3}
    inputs = { 'input': {
                'data' : '../data/testfiles/Kinase_inhibs.json.gz',
                'meta' : '../data/testfiles/Kinase_inhibs.metadata' }
        }
    service = 'core.dataset.filter.slice.v1'
    # start job
    job_id = squonk.run_job(service, options, inputs)

    squonk.job_wait(job_id)
"""

import configparser
import argparse
import json
import logging
import time
import sys
import os
from requests_toolbelt.multipart import decoder
try:
    from .SquonkAuth import SquonkAuth, SquonkAuthException
except:
    from SquonkAuth import SquonkAuth, SquonkAuthException
try:
    from .SquonkServer import SquonkServer
except:
    from SquonkServer import SquonkServer
try:
    from .SquonkJobDefinition import SquonkJobDefinition
except:
    from SquonkJobDefinition import SquonkJobDefinition
try:
    from .SquonkJob import SquonkJob
except:
    from SquonkJob import SquonkJob

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

# test for gzip

def _is_gzip(content):
    return content[:2]==b'1f8b'

class Squonk:

    def __init__(self,config_file='config.ini', config=None, user=None, password=None):
        """
        Instantiate a Squonk object.

        Create a Squonk object for running the Squonk Python API.
        Pass in configuration information such as urls , end points
        and username and password. Can be supplied via a config_file
        or a dictionary passed as an input parameter.
        If config is specified, then that is used otherwise it attempts
        to read config_file.

        Parameters
        ----------
        config_file : str
            Name of the configuration file. defaults to config.ini
        config : dict
            Configuration information
        user : str
            Username to override the config
        password : str
            Password to override the config

        Returns
        -------

        """

        # if config is passed in then use that

        if config:
            self._config = config

        # otherwise read the config file

        else:
            if not os.path.isfile(config_file):
                raise Exception(config_file + ' does not exist')
            self._config = {}
            settings = configparser.ConfigParser()
            settings._interpolation = configparser.ExtendedInterpolation()
            settings.read(config_file)

            self._config['client_id'] = settings.get('token', 'client_id')
            if 'client_secret' in settings['token']:
                self.token_client_secret = settings.get('token', 'client_secret')
            else:
                self._config['username'] = settings.get('token', 'username')
                self._config['password'] = settings.get('token', 'password')
            self._config['auth_url'] = settings.get('token', 'url')
            self._config['base_url'] = settings.get('general', 'base_url')
            self._config['services_endpoint'] = settings.get('ids', 'endpoint')
            self._config['jobs_endpoint'] = settings.get('job', 'endpoint')

        # override username and password if passed in
        if user:
            self._config['username'] = user
        if password:
            self._config['password'] = password

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

    def ping(self):
        """
        Checks that the service can be reached.

        Parameters
        ----------

        Returns
        -------
        boolean
            True if ok, False otherwise.

        """

        response = self.server.send('get', 'ping')
        if response:
            status_code = response.status_code
            if status_code == 200:
                return True
            else:
                return False
        else:
            return False

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
            logging.error("failed to get list of services")
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
            return response

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

        logging.debug('getting info for service:'+service_id)
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

    def job_yaml_template(self, filename, service, format='squonk'):
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
        format : str (optional)
            Format that the input data files will be in. squonk, mod, or sdf.
            The default is squonk

        """
        job_def = SquonkJobDefinition(service)
        info = self.list_full_service_info(service)
        if info:
            job_def.get_definition(info)
            job_def.template(filename, format)
        else:
            logging.error('Failed to get service definition from server')

    def yaml_from_inputs(self, service=None, options={}, inputs=[], yaml=None):
        """
        Generates a yaml file from job inputs specified 

        The input options for the job can be defined either by parameters
        passed into the function or read from a yaml file. The values supplied
        via parameters are validated against the service definition which is
        retreived from the server.

        Parameters
        ----------
        service : str
            Name of the service eg core.dataset.filter.slice.v1
        options : dict
            The jobs options in the form of a dictionary
        inputs : dict
            The jobs file inputs in the form of a dictionary
        yaml : str
            The name of a yaml file defining the job that will be generated.

        Returns
        -------

        """
        job = SquonkJob(self.server,service=service, options=options, inputs=inputs, end_point= self._config['jobs_endpoint'])
        if job.check_input():
            info = self.list_full_service_info(service)
            job.initialise(info)
            job.write_yaml(yaml)
        else:
            print('Failed checking job input')

    def run_job(self, service=None, options={}, inputs=[], yaml=None, convert_onserver=True):
        """
        Runs a Squonk job

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
            A yaml file defining the job. A template file can be generated
            using the function job_yaml_template

        Returns
        -------
        job_id : str
            The id of the job that has been started.

        """

        # create job
        job = SquonkJob(self.server,service=service, options=options, inputs=inputs, yaml=yaml, end_point= self._config['jobs_endpoint'])

        # check the input
        if job.check_input():

            # get service defintition
            info = self.list_full_service_info(job.get_service())

            # initialise job including validation against service definition
            job.initialise(info)

            # start job
            job_id = job.start(convert_onserver)

            return job_id
        else:
            print('Failed checking job input')
            return False

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

        logging.info('Deleting job ' + job_id)
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
            if 'status' in job_json:
                status = job_json['status']
            if status == 'ERROR':
                logging.debug(json.dumps(job_json, indent=4))
                if 'events' in job_json:
                    print(json.dumps(job_json['events']))
            return status

    def job_wait(self, job_id, dir=None, sleep=10, delete=True):
        """
        Waits for the specified job to finish and if it reaches a status of
        RESULTS_READY then reteives the jobs results.

        File created from the job are saved to the current directory or
        the specified directory

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
        status: str
            The job status

        """
        status = self.job_status(job_id)
        while status=='RUNNING':
            print('Job status:{} waiting for {} seconds'.format(status,sleep))
            time.sleep(sleep)
            status = self.job_status(job_id)
        if status == 'RESULTS_READY':
            self.job_results(job_id, dir)
            if delete:
                self.job_delete(job_id)
        else:
            print('Job Failed status='+status)
        return status

    # get content type from the header
    def _get_content_type(self,header):
        content_type = header['Content-Type'.encode()].decode()
        return content_type

    # get filename from the header, if there is one.
    def _get_filename(self,header):
        filename=''
        disp_key = 'Content-Disposition'.encode()
        if disp_key in header:
            content_disp = header[disp_key].decode()
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

        logging.info('getting results for job: ' + job_id)

        # stop the warning for a parse error due to whitespace in the
        # headers
        logging.getLogger("urllib3").setLevel(logging.ERROR)

        response = self.server.send('get', self._config['jobs_endpoint'] + job_id + '/results')

        # put the logging level back
        logging.getLogger("urllib3").setLevel(logging.INFO)
        if not response:
            return response
        logging.debug('parsing response ....')
        count=0
        multipart_data = decoder.MultipartDecoder.from_response(response)
        for part in multipart_data.parts:
            count+=1
            logging.debug("HEADER =========PART:"+str(count))
            logging.debug(part.headers)
            self._write_file(part,dir)
        return response

    # given part of a multipart response, write out a file.

    def _write_file(self,part,dir):

        # get file name, if there is one

        file_name = self._get_filename(part.headers)
        if len(file_name) < 2:
            logging.debug('No filename, ignoring')
            return

        # if the file is not gzipped but ends in gz, remove the .gz

        if not _is_gzip(part.content):
            if file_name.endswith('.gz'):
                file_name = file_name[:-3]

        # if the user gave a directory, prepend to file name

        if dir:
            if not os.path.exists(dir):
                logging.error('Specified directory: {} does not exist'.format(dir) )
                return
            else:
                file_name = os.path.join( dir, file_name)
        logging.info('Writing: ' + file_name)

        # extract the content
        content_type = self._get_content_type(part.headers)
        print(content_type)
        content = part.content
        mode = 'wb'
        if content_type != 'image/png':
            content = part.content.decode()
            mode = 'w'

        # write out the file.
        with open(file_name, mode) as f:
            f.write(content)
            f.close()

def main():

    # Get command line

    parser = argparse.ArgumentParser(description='Run Squonk from Python')
    parser.add_argument("-r", "--run", type=str, action="store", dest="yaml", help="Run job defined by specified yaml file (use --template to generate an example)", default=None)
    parser.add_argument("-s", "--service", type=str, action="store", dest="service", help="name of service to generate a yaml template from", default=None)
    parser.add_argument("-i", "--info", action="store_true", dest="info", help="output the service definition instead of creating a template", default=False)
    parser.add_argument("-f", "--format", type=str, action="store", dest="format", help="data format to generate the yaml template for ", default='squonk', choices=['squonk','mol','sdf'])
    parser.add_argument("-c", "--client", action="store_true", dest="client", help="perform conversions from sdf or mol on the client (default is server)", default=False)
    parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="output debug messages", default=False)
    parser.add_argument("-w", "--wait", type=int, action="store", dest="wait", help="wait time in seconds between checks for job finishing", default=10)
    parser.add_argument("-o", "--output", type=str, action="store", dest="dir", help="directory to write output to either job output or template generation", default=None)
    parser.add_argument("-u", "--user", type=str, action="store", dest="user", help="usrname to override the one in the config file", default=None)
    parser.add_argument("-p", "--password", type=str, action="store", dest="password", help="password to override the one in the config file", default=None)
    args = parser.parse_args()

    # debug output
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Job wait time: " + str(args.wait))
    else:
        logging.basicConfig(level=logging.INFO)
    if args.yaml:
        logging.debug("Got yaml file: " + args.yaml)
    if args.service:
        logging.debug("Got service: " + args.service)
 
    if not args.service and not args.yaml:
        print("You must specify --service or --yaml")
        exit()
    if args.service and args.yaml:
        print("You can't specify --service and --yaml")
        exit()

    # Create a Squonk object
    try:
        squonk = Squonk(user=args.user, password=args.password)
    except SquonkAuthException:
        print('Failed to authenticate with squonk service. Check your username and password')
        exit()

    # its a .yaml file, then run the job
    if args.yaml:
        input=args.yaml
        logging.info('Running job from yaml file: '+input)
        job_id = squonk.run_job(yaml=input, convert_onserver=not args.client)
        if job_id:
            logging.info('submitted job: ' + job_id)
            # wait for job to finish and get the results
            squonk.job_wait(job_id, sleep=args.wait, dir=args.dir)

    # Otherwise assume its a service name
    if args.service:
        file_name = args.service

        # prepend directory to filename if specified

        if args.dir:
            if not os.path.exists(args.dir):
                logging.error('Directory {} does not exist'.format(dir))
            file_name = os.path.join(args.dir, file_name)

        # full service info requested:

        if args.info:
            file_name += '.json'
            info = squonk.list_full_service_info(args.service)
            logging.info('Writing out file ' + file_name )
            with open(file_name, 'w') as f:
                f.write(json.dumps(info, indent=4))
                f.close()

        # yaml template requested

        else:
            file_name += '.yaml'
            logging.info('Writing out file ' + file_name )
            squonk.job_yaml_template(file_name, args.service, args.format)

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    main()
