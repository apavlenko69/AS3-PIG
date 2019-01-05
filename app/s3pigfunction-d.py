"""
    AS3 Photo Index Gallery
    Lambda function triggers for deleted images
"""

import boto3
import json
import simplejson
import urllib.parse


AWS_REGION = ''  # Specific value to be assigned in Lambda handler from Event parameter-object
JSON_CONFIG_FILE = 'pigconfig.json'  # Gallery configuration file name
CONFIG_FILE_TEMP_PATH = '/tmp/' + JSON_CONFIG_FILE  # /tmp is the only writable in Lambda
CONFIG_FILE_BUCKET_KEY = 'js/' + JSON_CONFIG_FILE  #
DDB_TABLE = 'S3PigImageAttributes'  # Value from SAM YAML template

print('Loading function')


def update_pig_config(image, s3bucket):
    """
    Deletes image entry from gallery JSON config

    :param image: S3 object key for uploaded image
    :param s3bucket: name of the bucket

    :return: None. Updated config file, log entries
    """

    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        ddb_table = boto3.resource('dynamodb', region_name=AWS_REGION).Table(DDB_TABLE)

        ddb_table.delete_item(Key={'FileName': image})

        ddb_reply = ddb_table.scan(Select="ALL_ATTRIBUTES")  # Full DB scan to pull updated data

        list_of_photos = [i for i in ddb_reply['Items']]

        with open(CONFIG_FILE_TEMP_PATH, 'w') as jfw:  # Updates gallery config json in Lambda /tmp
            simplejson.dump(list_of_photos, jfw, indent=4)

        with open(CONFIG_FILE_TEMP_PATH, 'rb') as content:  # Upload updated config back to S3 bucket
            s3_client.upload_fileobj(content, s3bucket, CONFIG_FILE_BUCKET_KEY)

    except Exception as e:
        print('Error while updating JSON config file: ', e)


def lambda_handler(event, context):
    """
    Lambda handler function runs once trigger is activated by configured event.

    """

    try:

        global AWS_REGION

        AWS_REGION = event['Records'][0]['awsRegion']

        s3objkey = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        bucket = event['Records'][0]['s3']['bucket']['name']

        print("\nDeleting < {} > image from album [- {} -]".format(str(s3objkey).split('/')[-1],
                                                                         str(s3objkey).split('/')[-2]))

        update_pig_config(s3objkey, bucket)

        print("\nTime remaining (MS): {}\n".format(context.get_remaining_time_in_millis()))

    except Exception as e:
        print('ERROR: ', e)
