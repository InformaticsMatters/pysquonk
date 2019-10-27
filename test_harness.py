from squonk import Squonk
import os
import sys
import logging
import argparse


# Get command line
parser = argparse.ArgumentParser(description='Python Squonk API test harness')
parser.add_argument("username", type=str, help="Username on the service")
parser.add_argument("password", type=str, help="Password on the service")
parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="output debug messages", default=False)

args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

# user name and password and set config

username = args.username
if not username:
    print('You need to set specify username')
    sys.exit(1)
password = args.password
if not password:
    print('You need to set specify password')
    sys.exit(1)

auth_url = 'https://sso.apps.xchem.diamond.ac.uk/auth/realms/xchem/protocol/openid-connect/token'
base_url = 'https://jobexecutor.apps.xchem.diamond.ac.uk/jobexecutor/rest/v1'
service = 'core.dataset.filter.slice.v1';

config = {
  'base_url' : base_url,
  'auth_url' : auth_url,
  'username' : username,
  'password' : password,
  'services_endpoint' : 'services/',
  'jobs_endpoint' : 'jobs/'
}

# Create a Squonk object

print('Cresting squonk object ...')
squonk = Squonk(config=config)

# list full service info

print('list_full_service_info ...')
info = squonk.list_full_service_info(service)
print(info)
print('list_service_info ...')
info = squonk.list_service_info(service)
print(info)
print('list_service_info_field ...')
field = squonk.list_service_info_field(service,'name')
print(field)

# list service ids

print('list_service_ids ...')
list = squonk.list_service_ids()
print(list)

# save yaml template

print('job_yaml_template ...')
squonk.job_yaml_template('slice_template.yaml', 'core.dataset.filter.slice.v1')

# setup jobinputs to pass to command

options = {"skip":2,"count":3}
inputs = { 'input': {
            'data' : 'data/testfiles/Kinase_inhibs.json.gz',
            'meta' : 'data/testfiles/Kinase_inhibs.metadata' }
        }
service = 'core.dataset.filter.slice.v1'

# write yaml
print('yaml_from_inputs ...')
job = squonk.yaml_from_inputs(service, options, inputs, 'example_from_job.yaml')

# start job
print('run_job ...')
job_id = squonk.run_job(service, options, inputs)
print(job_id)

# run again
print('run_job again ...')
job_id2 = squonk.run_job(service, options, inputs)
print(job_id2)

# get status
print('job_status ...')
status = squonk.job_status(job_id2)
print(status)

# list_jobs
print('list jobs ...')
list = squonk.list_jobs()

# wait for results
print('job_wait ' + job_id2)
squonk.job_wait(job_id2)

# get results
print('get results of job:' + job_id)
squonk.job_results(job_id)

# delete job
print('delete job:' + job_id)
squonk.job_delete(job_id)

# delete all jobs
print('delete all jobs')
squonk.job_delete_all
