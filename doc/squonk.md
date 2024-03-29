Module squonk
=============
A Python wrapper around the Informatics Matters Squonk REST API.

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

Functions
---------

    
`main()`
:   

Classes
-------

`Squonk(config_file='config.ini', config=None, user=None, password=None)`
:   Instantiate a Squonk object.
    
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

    ### Methods

    `job_delete(self, job_id)`
    :   Delete the specified job
        
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

    `job_delete_all(self)`
    :   Delete all jobs for the current user
        
        Parameters
        ----------
        
        Returns
        -------

    `job_results(self, job_id, dir=None)`
    :   Get the results of the given job
        
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

    `job_status(self, job_id)`
    :   Get the status of a job from its job_id
        
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

    `job_wait(self, job_id, dir=None, sleep=10, delete=True)`
    :   Waits for the specified job to finish and if it reaches a status of
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

    `job_yaml_template(self, filename, service, format='squonk')`
    :   Outputs a yaml template for a specified service.
        
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

    `list_full_service_info(self, service_id)`
    :   Returns the service name and description.
        
        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1
        
        Returns
        -------
        dict
            Dictionary containing service id, name and description

    `list_jobs(self)`
    :   List all the job ids for jobs owned by the user.
        
        Parameters
        
        Returns
        -------
        []str
            List of job ids of jobs for the current user

    `list_service_ids(self)`
    :   Returns a list of all the service ids
        
        Parameters
        ----------
        
        Returns
        -------
        []str
            List of all the service ids

    `list_service_info(self, service_id)`
    :   Returns the service name and description.
        
        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1
        
        Returns
        -------
        dict
            Dictionary containing service id, name and description

    `list_service_info_field(self, service_id, field)`
    :   Returns a specified field from the service info
        
        Parameters
        ----------
        service_id : str
            Name of the service eg core.dataset.filter.slice.v1
        
        Returns
        -------
        str
            Field from the service info.

    `list_services(self)`
    :   Returns all the available service definitions
        
        Parameters
        ----------
        
        Returns
        -------
        json
            Json for all the available services

    `ping(self)`
    :   Checks that the service can be reached.
        
        Parameters
        ----------
        
        Returns
        -------
        boolean
            True if ok, False otherwise.

    `run_job(self, service=None, options={}, inputs=[], yaml=None, convert_onserver=True)`
    :   Runs a Squonk job
        
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

    `yaml_from_inputs(self, service=None, options={}, inputs=[], yaml=None)`
    :   Generates a yaml file from job inputs specified 
        
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