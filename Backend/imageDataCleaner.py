from __future__ import print_function
from boto3.dynamodb.conditions import Key, Attr

import boto3
import urllib
import json, simplejson


# *************************************************************
#   Deletes DynamoDB item after deleting image file from bucket
#  
# *************************************************************

v_region_name = 'eu-west-1'
v_ddb_table_1_name = 'T1_RkLabels'
v_ddb_table_2_name = 'T2_ExifTags'
v_ddb_table_4_name = 'T4_AllImgAttributes'

# JSON structure with all image data for use on client side with JavaScript
configFileJSON = 'GalleryConfig.json'

v_client = boto3.client('s3')
v_s3 = boto3.resource('s3')

# Lambda handler
def deleteImageData(event, context):
    # Open connection to DynamoDB
    # Deletes item with keys

    v_ddb = boto3.resource('dynamodb', v_region_name)
    v_ddb_table_1 = v_ddb.Table(v_ddb_table_1_name)
    v_ddb_table_2 = v_ddb.Table(v_ddb_table_2_name)
    v_ddb_table_4 = v_ddb.Table(v_ddb_table_4_name)

    for record in event['Records']:
        v_bucket = record['s3']['bucket']['name']
        v_s3objkey = urllib.unquote_plus(record['s3']['object']['key'].encode('utf8'))

        v_S3obj1 = v_ddb_table_1.query(
            KeyConditionExpression=Key('S3ObjKey').eq(v_s3objkey)
        )

        for item1 in v_S3obj1['Items']:
            #print(v_s3objkey, item1['RkLabel'])
            v_ddb_table_1.delete_item(
                Key={
                    'S3ObjKey': v_s3objkey,
                    'RkLabel': item1['RkLabel']
                }
            )

        v_S3obj = v_ddb_table_2.query(
            KeyConditionExpression=Key('S3ObjKey').eq(v_s3objkey)
        )

        for item in v_S3obj['Items']:
            #print(v_s3objkey, item['ShootingDateTime'])
            v_ddb_table_2.delete_item(
                Key={
                    'S3ObjKey': v_s3objkey,
                    'ShootingDateTime': item['ShootingDateTime']
                }
            )

        v_ddb_table_4.delete_item(
            Key={
                'FileName': v_s3objkey,
            }
        )

        # Full DB scan to pull updated data
        resp = v_ddb_table_4.scan(
        Select="ALL_ATTRIBUTES",
        )
        # List of images with all attributes pulled from DB for creating JSON config file
        imageT4Atrib = []
        for i in resp['Items']:
            imageT4Atrib.append(i)

        # Creating JSON config file in /tmp
        with open('/tmp/'+configFileJSON, 'wb') as cf_json:
            #print(simplejson.dumps(imageT4Atrib,cf_json, indent=4, separators=(',', ': ')))
            simplejson.dump(imageT4Atrib,cf_json,indent=4,separators=(',', ': '))

        # Put JSON config file to target S3 bucket in /v2/js subfolder
        v_jsonConfigS3 = "v2/js/" + configFileJSON
        with open('/tmp/'+configFileJSON, 'rb') as cf_json:
            v_client.upload_fileobj(cf_json, bucket, v_jsonConfigS3)
