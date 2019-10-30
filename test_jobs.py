from squonk import Squonk
import os
import sys
import logging
import argparse
import glob
import getpass


# Get command line
parser = argparse.ArgumentParser(description='Python Squonk API test jobs')
parser.add_argument("username", type=str, help="Username on the service")
parser.add_argument("password", type=str, help="Password on the service")
parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="output debug messages", default=False)

args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

# user name and password and set config

username = args.username
if not username:
    username = input('Username')
password = args.password
if not password:
    password = getpass.getpass('Password')

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

yamls=glob.glob('yaml/*.yaml')

for yaml in yamls:
    file_base, file_ext = os.path.splitext(yaml)
    # start job
    print('run_job: ' + file_base)
    outdir = 'job_output/' + file_base
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    job_id = squonk.run_job(yaml=yaml)
    print(job_id)

    # wait for results
    print('job_wait ' + job_id)
    squonk.job_wait(job_id, dir=outdir)
