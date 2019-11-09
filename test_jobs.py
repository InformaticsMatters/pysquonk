import os
import sys
import logging
import argparse
import glob
import getpass
from squonk import Squonk
from utils import peek

# this script runs all the jobs defined in the yaml directory and
# tries to do some tests to see if they worked or not.

def check_exists(outdir,epath):
    if not os.path.exists(epath):
        print('ERROR: job {} file {} does not exist'.format(job_name,epath))
        exit()
    else:
        print('OK: job {} file {} exists'.format(job_name,epath))

def check_value(expected,actual,item):
    if expected == actual:
        print('OK: value {} as expected {}'.format(item,expected))
    else:
        print('ERROR: value {} expected {} got {}'.format(item,expected,actual))
        exit()

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
#service = 'core.dataset.filter.slice.v1';

config = {
  'base_url' : base_url,
  'auth_url' : auth_url,
  'username' : username,
  'password' : password,
  'services_endpoint' : 'services/',
  'jobs_endpoint' : 'jobs/'
}

# expected output files

expected_files = {
    'cdk.donors_acceptors' :
        { 'data': 'output_output.data',
          'meta': 'output_metadata',
          'field': 'HBA_CDK',
          'nrecs': 36},
    'core.dataset.filter.slice.v1' :
        { 'data': 'output_output.data',
          'meta': 'output_metadata',
          'nrecs': 5},
    'core.dataset.merger.v1' :
        { 'data': 'output_output.data',
          'meta': 'output_metadata',
          'nrecs': 339},
    'pipelines.dmpk.sygnature.tmax_cmax_sim.1' :
        { 'other': 'output_output.png' },
    'pipelines.rdkit.cluster.butina' :
        { 'data': 'output_data',
          'field': 'Cluster',
          'nrecs': 36,
          'meta': 'output_metadata'},
    'pipelines.rdkit.maxminpicker.enrich.1' :
        { 'data': 'output_data',
          'meta': 'output_metadata',
          'nrecs': 100},
    'pipelines.rdkit.maxminpicker.simple.1' :
        { 'data': 'output_data',
          'meta': 'output_metadata',
          'nrecs': 100},
    'pipelines.rdkit.o3da.basic' :
        { 'data': 'output_data',
          'meta': 'output_metadata',
          'nrecs': 36},
    'pipelines.rdkit.screen.multi' :
        { 'data': 'output_output.data',
          'meta': 'output_metadata',
          'nrecs': 21},
    'pipelines.rdkit.sucos.basic' :
        { 'data': 'output_data',
          'field': 'SuCOS_Score',
          'nrecs': 6,
          'meta': 'output_metadata'},
    'rdkit.calculators.canonical_smiles' :
        { 'data': 'output_output.data',
          'nrecs': 36,
          'field': 'CanSmiles_RDKit',
          'meta': 'output_metadata'},
    'rdkit.calculators.lipinski' :
        { 'data': 'output_output.data',
          'nrecs': 23,
          'field': 'LogP_RDKit',
          'meta': 'output_metadata'},
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

    if not job_name in expected_files:
        print('No checks defined for :' + job_name)
        continue

    # check if we got the files
    if 'other' in expected_files[job_name]:
        epath = os.path.join(outdir,expected_files[job_name]['other'])
        check_exists(outdir,epath)
    if 'meta' in expected_files[job_name]:
        epath = os.path.join(outdir,expected_files[job_name]['meta'])
        check_exists(outdir,epath)
        file_info = peek(epath,False)
        check_value('meta', file_info['type'], 'file type')
        check_value(True, file_info['recent'], 'file timestamp recent')
        
    if 'data' in expected_files[job_name]:
        epath = os.path.join(outdir,expected_files[job_name]['data'])
        check_exists(outdir,epath)
        field=None
        if 'field' in expected_files[job_name]:
            field=expected_files[job_name]['field']
        file_info = peek(epath,False,field)
        check_value('data', file_info['type'], 'file type')
        check_value(True, file_info['recent'], 'file timestamp')
        if 'nrecs' in expected_files[job_name]:
            check_value(expected_files[job_name]['nrecs'], file_info['nrecs'], 'number of records')
        if field:
            if file_info['fields']:
                print('OK Field: ' + field + ' ' + str(file_info['fields']) )
            else:
                print('OK Field: ' + field + ' not present ')

    count+=1

print("Finished {} jobs".format(count))

