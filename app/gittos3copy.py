"""
    This function is a part of CloudFormation deployment of AS3-PIG service.
    Depends on SAM config file.
"""

import boto3
import json
import cfnresponse
import urllib.request
from urllib.parse import urlparse

AWS_REGION = ''  # Specific value to be assigned in Lambda handler from Event parameter-object
s3_client = boto3.client('s3', region_name=AWS_REGION)


def save_to_local(url):
    branch = 'master'  # Name of Git branch as part of URL path of raw file link

    url_path = urlparse(url).path
    path_as_list = url_path.split("/")
    fld_depth = path_as_list.index(branch)
    full_path_list = path_as_list[:fld_depth:-1]
    local_file_path = '/tmp/' + path_as_list[-1]

    s3_file_key = ''
    for f in full_path_list[::-1]:
        s3_file_key += "/" + f

    urllib.request.urlretrieve(url, local_file_path)
    return local_file_path, s3_file_key[1:]


def copy_to_s3(url, bucket):
    loc_file_path, s3_key = save_to_local(url)
    with open(loc_file_path, 'rb') as content:  # Upload to S3 bucket
        s3_client.upload_fileobj(content, bucket, s3_key)


def lambda_handler(event, context):
    """Invokes as part of deployment"""

    print("Received event: " + json.dumps(event, indent=2))

    global AWS_REGION

    AWS_REGION = event['ResourceProperties']['Region']

    if event['RequestType'] == 'Create':

        properties = event['ResourceProperties']  # get the properties set in the CloudFormation resource
        urls = properties['SourceUrls']
        bucket = properties['TargetS3BucketName']

        try:
            for url in urls:
                copy_to_s3(url, bucket)

        except Exception as e:
            print(e)
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Response': 'Failure'})
            return

    elif event['RequestType'] == 'Delete':
        pass  # Add cleanup procedure

    cfnresponse.send(event, context, cfnresponse.SUCCESS, {'Response': 'Success'})
