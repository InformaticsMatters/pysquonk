from squonk import Squonk
import os
import sys
import logging
import argparse
import glob
import getpass


# Get command line
parser = argparse.ArgumentParser(description='Python Squonk API test jobs')
parser.add_argument("-u", "--username", type=str, help="Username on the service", dest='username')
parser.add_argument("-p", "--password", type=str, help="Password on the service", dest='password')
parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="output debug messages", default=False)
parser.add_argument("-r", "--run", type=str, help="Service to run. Assumes the existence of a file called yaml/service.yaml", dest='yaml', default=None)

args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# user name and password and set config

username = args.username
if not username:
    username = input('Enter Username:')
password = args.password
if not password:
    password = getpass.getpass('Enter Password:')

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

print('Creating squonk object ...')
squonk = Squonk(config=config)

# get list of jobs

yamls=[]
if args.yaml:
    file_name = 'yaml/' + args.yaml + '.yaml'
    if os.path.isfile(file_name):
        yamls.append(file_name)
    else:
        print('ERROR: File does not exist: ' + file_name)
        exit()
else:
    yamls=glob.glob('yaml/*.yaml')

count=0
for yaml in yamls:
    file_base, file_ext = os.path.splitext(yaml)
    # start job
    job_name = file_base[5:]
    print('run_job: ' + job_name)
    outdir = './test_output/' + job_name
    if not os.path.exists(outdir):
        print('creating:' + outdir)
        os.mkdir(outdir)
    job_id = squonk.run_job(yaml=yaml)
    if job_id:
        print('Submitted job:' + job_id)
    else:
        print('ERROR: job failed: ' + yaml)
        exit()
        

    # wait for results
    print('job_wait ' + job_id)
    squonk.job_wait(job_id, dir=outdir)
    count+=1

print("Finished {} jobs".format(count))
