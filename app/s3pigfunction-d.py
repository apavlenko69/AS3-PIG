"""
    AS3 Photo Index Gallery
    Lambda function for deleted images
"""

import boto3
import json

aws_region = ''  # Specific value defined in Lambda handler from Event parameter object

JSON_CONFIG_FILE = 'pigconfig.json'

print('Loading function')


def is_key_exists(client, bucket, key):
    """
    :param client: S3 boto3 client
    :param bucket: S3 bucket
    :param key: S3 object key (path to file within bucket)
    :return: True if object exists in bucket, False if not
    """

    response = client.list_objects_v2(
        Bucket=bucket,
        Prefix=key,
    )
    for obj in response.get('Contents', []):
        if obj['Key'] == key:
            return True
        else:
            return False


def update_pig_config(image, s3bucket):
    """
    Deletes image entry from gallery JSON config

    :param image: S3 object key for uploaded image
    :param s3bucket: name of the bucket

    :return: None. Updated config file, log entries
    """

    try:
        config_file_temp_path = '/tmp/' + JSON_CONFIG_FILE
        config_file_bucket_key = 'js/' + JSON_CONFIG_FILE  # Todo: Rebuild to avoid hardcoded path to config

        s3_client = boto3.client('s3', region_name=aws_region)

        with open(config_file_temp_path, 'wb') as data:  # Download pigconfig.json from S3 to Lambda /tmp
            s3_client.download_fileobj(s3bucket, config_file_bucket_key, data)

        with open(config_file_temp_path, 'r') as file:  # Read JSON structure
            json_object = json.load(file)

        for i, item in enumerate(json_object):
            if item['FileName'] == image:  # Image for deletion

                del json_object[i]

                with open(config_file_temp_path, 'w') as jfw:  # Updates gallery config json in Lambda /tmp
                    json.dump(json_object, jfw, indent=4)

                with open(config_file_temp_path, 'rb') as content:  # Upload updated config back to S3 bucket
                    s3_client.upload_fileobj(content, s3bucket, config_file_bucket_key)

    except Exception as e:
        print('Error while updating JSON config file: ', e)


def lambda_handler(event, context):
    """
    Lambda handler function runs once trigger is activated by configured event.

    """

    try:

        global aws_region

        aws_region = event['Records'][0]['awsRegion']

        s3objkey = event['Records'][0]['s3']['object']['key']
        bucket = event['Records'][0]['s3']['bucket']['name']

        print("\nDeleting < {} > image from album [- {} -]".format(str(s3objkey).split('/')[-1],
                                                                         str(s3objkey).split('/')[-2]))

        update_pig_config(s3objkey, bucket)

        print("\nTime remaining (MS): {}\n".format(context.get_remaining_time_in_millis()))

    except Exception as e:
        print('ERROR: ', e)
