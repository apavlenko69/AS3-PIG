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


def get_path_and_key(url):
    branch = 'master'  # Name of Git branch as part of URL path of raw file link

    url_path = urlparse(url).path
    path_as_list = url_path.split("/")
    fld_depth = path_as_list.index(branch)
    full_path_list = path_as_list[:fld_depth:-1]
    local_file_path = '/tmp/' + path_as_list[-1]

    s3_file_key = ''
    for f in full_path_list[::-1]:
        s3_file_key += "/" + f

    return local_file_path, s3_file_key[1:]


def copy_to_s3(url, bucket):
    s3_client = boto3.client('s3', region_name=AWS_REGION)

    loc_file_path, s3_key = get_path_and_key(url)
    urllib.request.urlretrieve(url, loc_file_path)

    # with open(loc_file_path, 'rb') as content:  # Binary upload to S3 bucket
    #    s3_client.upload_fileobj(content, bucket, s3_key)
    s3_client.upload_file(loc_file_path, bucket, s3_key)  # File upload to S3


def clean_bucket(bucket):

    s3_client = boto3.client('s3', region_name=AWS_REGION)
    objects_to_delete = s3_client.list_objects_v2(Bucket=bucket)

    delete_keys = {'Objects': []}
    delete_keys['Objects'] = [{'Key': k} for k in [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]

    delete_response = s3_client.delete_objects(Bucket=bucket, Delete=delete_keys)

    return delete_response


def lambda_handler(event, context):
    """Invokes as part of deployment"""

    print("Received event: " + json.dumps(event, indent=2))

    global AWS_REGION
    AWS_REGION = event['ResourceProperties']['awsRegion']
    print("AWS Region is " + AWS_REGION)

    properties = event['ResourceProperties']  # get the properties set in the CloudFormation resource
    urls = properties['SourceUrls']
    bucket = properties['TargetS3BucketName']

    if event['RequestType'] == 'Create':
        try:
            for url in urls:
                copy_to_s3(url, bucket)

        except Exception as e:
            print(e)
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Response': 'Failure'})
            return

    elif event['RequestType'] == 'Delete':
        # Bucket cleanup procedure
        try:
            clean_bucket(bucket)

        except Exception as e:
            print(e)
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Response': 'Failure'})
            return

    cfnresponse.send(event, context, cfnresponse.SUCCESS, {'Response': 'Success'})
