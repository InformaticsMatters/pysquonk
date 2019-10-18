Module SquonkJob
================
A SquonkJob is a particular instance of a SquonkJobDefinition
ie set of options, input files and a job_id.
(A SquonkJobDefinition represents the service definition of a job)

This includes methods to create start a job from either passed in    
parameters or input yaml file.

Classes
-------

`SquonkJob(server, service=None, options={}, inputs={}, yaml=None, end_point='jobs/')`
:   

    ### Methods

    `get_status(self, job_id)`
    :

    `initialise(self)`
    :

    `start(self)`
    :   Submit the job to the server
        
        Parameters
        ----------
        
        Returns
        -------
        str
            string containing the job id.

    `validate(self)`
    :

    `write_yaml(self, yaml_name)`
    :