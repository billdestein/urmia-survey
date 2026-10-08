"""Download a CSV using locally configured AWS credentials, including SSO sessions."""
import argparse
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

parser=argparse.ArgumentParser()
parser.add_argument('--profile', required=True)
parser.add_argument('--region', required=True)
parser.add_argument('--url', required=True)
parser.add_argument('--output', required=True)
args=parser.parse_args()
host=urlparse(args.url)
if host.scheme!='https' or not host.hostname or not host.hostname.endswith('.amazonaws.com'):
    parser.error('Use the HTTPS API Gateway export URL from the stack outputs.')
session=boto3.Session(profile_name=args.profile,region_name=args.region)
credentials=session.get_credentials()
if credentials is None: parser.error('No AWS credentials found for this profile.')
request=AWSRequest(method='GET',url=args.url)
SigV4Auth(credentials.get_frozen_credentials(),'execute-api',args.region).add_auth(request)
try:
    with urlopen(Request(args.url,headers=dict(request.headers)),timeout=70) as result:
        content=result.read()
    with open(args.output,'xb') as output: output.write(content)
except Exception as error:
    sys.exit(f'Export failed: {type(error).__name__}. Check credentials, permission, URL, and output path.')
print(f'Saved CSV to {args.output}')
