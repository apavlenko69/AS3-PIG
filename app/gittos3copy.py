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
    """
    Fetching S3 key from full URL and creates path for temporary local file

    :param url:
    :return:
    """
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


def hack_js_code(bucket, region, file='/tmp/s3pi_grid_template.js'):
    """
    Prepares frontend javascript code for use with specific AWS region and bucket

    :param bucket: S3 bucket name
    :param region: AWS region
    :param file: javascript source file name
    :return: modified code of javascript
    """
    patterns = ['<BUCKET-NAME>',  # Tags in javascript code for replacement: bucket, region, etc.
                '<AWS-REGION>',
                '<GOOGLE_API_KEY>',
                ]

    replacers = [bucket, region, 'AIzaSyDCBDh5PrbSC9G-m4G3NpQYjymApurLkCc']

    zipped = list(zip(patterns, replacers))

    with open(file, "r") as jsf:
        code = jsf.readlines()

    hacked_code = []
    for line in code:
        for z in zipped:
            if line.find(z[0]) != -1:
                line = line.replace(z[0], z[1])
        hacked_code.append(line)

    hacked_temp_file = file + '_'
    with open(hacked_temp_file, "a") as jf:
        for hline in hacked_code:
            jf.write(hline)

    s3_client = boto3.client('s3', region_name=AWS_REGION)
    target_s3_key = 'js/s3pi_grid.js'

    s3_client.upload_file(hacked_temp_file,
                          bucket,
                          target_s3_key,
                          ExtraArgs={'ContentType': "application/javascript"}
                          )


def copy_to_s3(url, bucket):
    """
    Uploads file from URL to S3 bucket

    :param url: URL of file
    :param bucket: bucket name
    :return: None
    """
    metadata = {
        "html": "text/html; charset=utf-8",
        "css": "text/css",
        "js": "application/javascript",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "txt": "text/plain",
    }

    s3_client = boto3.client('s3', region_name=AWS_REGION)

    loc_file_path, s3_key = get_path_and_key(url)
    urllib.request.urlretrieve(url, loc_file_path)
    ext = s3_key.split('/')[-1].split('.')[-1]

    if loc_file_path == '/tmp/s3pi_grid_template.js':
        hack_js_code(bucket, AWS_REGION, loc_file_path)

    else:
        for e, m in metadata.items():
            if e == ext:
                s3_client.upload_file(loc_file_path,
                                      bucket,
                                      s3_key,
                                      ExtraArgs={'ContentType': m, 'ACL': 'public-read'})


def clean_bucket(bucket):
    """
        Deletes all objects in bucket including empty folders.
        Required before deleting of CloudFormation stack
    """
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
