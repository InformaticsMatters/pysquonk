import os
import sys
import logging
import argparse
import getpass
from squonk import Squonk
from utils import peek
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


# Get command line
parser = argparse.ArgumentParser(description='Python Squonk API test harness')
parser.add_argument("-u", "--username", type=str, help="Username on the service", dest='username')
parser.add_argument("-p", "--password", type=str, help="Password on the service", dest='password')
parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="output debug messages", default=False)
parser.add_argument("-e", "--error", type=str, help="Run error check", dest='err_name', default=None)

args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# user name and password and set config
username = args.username
if not username:
    username = input('Enter Username >')
password = args.password
if not password:
    password = getpass.getpass('Enter Password >')

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

print('Starting test ========================================')

if args.err_name:
    err_name = args.err_name
    print('Running error test:' + err_name)
    sa = SquonkAuth(auth_url, username, password)
    if err_name == 'no_yaml':
        ss = SquonkServer(sa, base_url)
        job = SquonkJob(ss)

# Create a Squonk object

print('creating squonk object ...')
squonk = Squonk(config=config)

# ping does not exist on diamond
#if squonk.ping():
#    print('service ping OK')
#else:
#    print('service ping FAILED')
#    exit()

# list full service info

info = squonk.list_full_service_info(service)
if 'inputDescriptors' in info:
    print('OK - list_full_service_info inputDescriptors found')
else:
    print('FAILED -  list_full_service_info inputDescriptors not found')
    exit()

# list service info

info = squonk.list_service_info(service)
if info[0]['id'] == service:
    print('OK list_service_info')
else:
    print('FAILED: list_service_info')
    exit()

field = squonk.list_service_info_field(service,'name')
if field=='Dataset slice selector':
    print('OK service name:Dataset slice selector')
else:
    print('FAILED squonk.list_service_info_field')
    exit()

# list service ids

list = squonk.list_service_ids()
if service in list and len(list)>10:
    print('OK: number of services={} and service {} found'.format(len(list),service))
else:
    print('FAILED: squonk.list_service_ids')
    exit()
#print(list)

# save yaml template

template_name='test_output/slice_template.yaml'
print('generating job_yaml_template: ' + template_name)
squonk.job_yaml_template(template_name, 'core.dataset.filter.slice.v1')
if os.path.isfile(template_name):
    print('OK: Template file found: ' + template_name)
else:
    print('ERROR: File does not exist: ' + template_name)
    exit()

# setup jobinputs to pass to command

options = {"skip":2,"count":3}
inputs = { 'input': {
            'data' : 'data/Kinase_inhibs.json.gz',
            'meta' : 'data/Kinase_inhibs.metadata' }
        }
service = 'core.dataset.filter.slice.v1'

# write yaml
yaml_file = 'test_output/example_from_job.yaml'
print('generating yaml_from_inputs: ' + yaml_file)
job = squonk.yaml_from_inputs(service, options, inputs, 'test_output/example_from_job.yaml')
if os.path.isfile(yaml_file):
    print('OK: yaml file found: ' + yaml_file)
else:
    print('ERROR: File does not exist: ' + yaml_file)
    exit()

# start job
job_id = squonk.run_job(service, options, inputs)
if job_id:
    print('OK: started job:'+job_id)
else:
    print('FAILED to start job')
    exit()

# run again
job_id2 = squonk.run_job(service, options, inputs)
if job_id2:
    print('OK: started job:'+job_id2)
else:
    print('FAILED to start job2')
    exit()

# get status
status = squonk.job_status(job_id2)
if status=='RUNNING' or status=='RESULTS_READY':
    print('OK job2 status:' + status)
else:
    print('FAILED job2 status:' + status)
    exit()

# list_jobs
print('list jobs ...')
list = squonk.list_jobs()
if len(list)>0:
    print('OK number of jobs running:' + str(len(list)))
else:
    print('FAILED number of jobs running:' + str(len(list)))
    exit()

# wait for results
status=squonk.job_wait(job_id2, dir='test_output')
if status=='RESULTS_READY':
    print('OK job2 wait status:' + status)
else:
    print('FAILED job2 wait status:' + status)
    exit()

# get results
print('get results of job:' + job_id)
response = squonk.job_results(job_id, dir='test_output')
if response:
    print('OK got results')
else:
    print('FAILED getting results')
    exit()

file_info = peek('test_output/output_output.data',False)
if file_info['recent']:
    print('OK: recently generated file')
else:
    print('FAILED: recently generated file')
    exit()
if file_info['nrecs'] == 3:
    print('OK: number of records = 3')
else:
    print('FAILED: number of records in file')
    exit()
if file_info['type'] == 'data':
    print('OK: type is squonk data')
else:
    print('FAILED: file type is wrong')
    exit()
#print(file_info)

# delete job
response = squonk.job_delete(job_id)
if response:
    print('OK deleted job')
else:
    print('FAILED deleting job')
    exit()

# delete all jobs
print('delete all jobs')
squonk.job_delete_all

print('OK: Test completed')
