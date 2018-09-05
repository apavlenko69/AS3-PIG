# *********************************************************************************************
# Lambda function for uploaded into S3 image.
# Once image "created" inside bucket next happens:
# 1) AWS Rekognition detects labels and writes results in scalars to Table1
# 2) downloading image, exifread reads tags and writes subset of tags in scalars to Table2
# 3) JSON config: keeps all attributes in T4 table and export its data/structure to JSON on S3
#       version from 10-March-2017
# **********************************************************************************************

from __future__ import print_function

import boto3
import exifread
import time
import json, simplejson
import urllib
import mimetypes
import os.path

myRegion = 'eu-west-1'

myTable_1_Params = ['T1_RkLabels','S3ObjKey','RkLabel']
myTable_2_Params = ['T2_ExifTags','S3ObjKey','ShootingDateTime']
#myTable_3_Params = ['T3_Genres','S3ObjKey','Genre'] # reserved for genres information
myTable_4_Params = ['T4_AllImgAttributes','FileName','UploadTimeStamp']

rk_limit = 15*1024*1024 # AWS Rekognition limit on S3 file size

# Allowed mime types
imageMimeTypes = [
'image/jpeg',
'image/gif',
'image/png',
'image/pjpeg',
'image/bmp'
]

v_s3client = boto3.client('s3')
v_rek_client = boto3.client('rekognition', region_name=myRegion)
#v_ddb_client = boto3.client('dynamodb', region_name=myRegion)

# JSON structure with all image data for use on client side with JavaScript
configFileJSON = 'GalleryConfig.json'

# Lambda handler
def addImageData(event, context):

    for record in event['Records']:
        v_bucket = record['s3']['bucket']['name']
        v_s3objkey = urllib.unquote_plus(record['s3']['object']['key'].encode('utf8'))
        v_fsize = record['s3']['object']['size']

        # Validator of lowercase extention
        if os.path.splitext(v_s3objkey)[1].isupper():
            # Rename (copy/delete) file to have lowercase extention
            copy_params = {
                'Bucket':  v_bucket,
                'Key': v_s3objkey
            }
            proper_name = os.path.splitext(v_s3objkey)[0] + os.path.splitext(v_s3objkey)[1].lower()
            v_s3client.copy(copy_params, v_bucket, proper_name)
            v_s3client.delete_object(Bucket=v_bucket, Key=v_s3objkey)
            v_s3objkey = proper_name

        if (mimetypes.MimeTypes().guess_type(v_s3objkey)[0] in imageMimeTypes) and (v_fsize < rk_limit):
            print('Processing image:', v_s3objkey)

            # Invoke AWS Rekognition to find labels
            v_labels = discoverImageLabels(v_bucket, v_s3objkey)

            # Pulling EXIF meta data
            v_tags = extractExifData(v_bucket, v_s3objkey)

            # Updating JSON config file on S3 bucket for in browser use
            updateJSONconfig(v_bucket,v_s3objkey,v_labels,v_tags)
        elif mimetypes.MimeTypes().guess_type(v_s3objkey)[0] not in imageMimeTypes:
            print('Info:', v_s3objkey, 'skipped as it\'s not an image')
        elif v_fsize >= rk_limit:
            print('Info:', v_s3objkey, 'skipped as it\'s tp big to process by Rekognition')


# ===============================================================
# Function for fetching Exif tags from image file
# ToDo: Is it possible to not download file?
# ===============================================================
def extractExifData(bucket, image):

    with open('/tmp/tmpimage.jpg', 'wb') as data:
        v_s3client.download_fileobj(bucket, image.decode('utf8'), data)

    tf = open('/tmp/tmpimage.jpg', 'rb')
    exif_tags = exifread.process_file(tf, details = False)

    v_params = {
            'Item': {
            myTable_2_Params[1]: image,
            myTable_2_Params[2]: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            }
    }

    # List of useful EXIF tags
    v_useful_exif_tags = [
        'Image Make',
        'Image Model',
        'Image DateTime',
        'EXIF ISOSpeedRatings',
        'EXIF ExposureTime',
        'EXIF FNumber',
        'EXIF ExposureProgram',
        'EXIF ExposureMode'
        'EXIF FocalLength',
        'EXIF ExifImageWidth',
        'EXIF ExifImageLength'
        ]

    exifs_arr = {}

    for tag in exif_tags.keys():
        # Filtering whole EXIF array to select only list of useful
        if tag in (v_useful_exif_tags):
            if tag == 'Image DateTime':
            # Creating datetime in ISO format
                v_datetime = time.strptime(exif_tags[tag].printable, "%Y:%m:%d %H:%M:%S")
                v_rangeKey = time.strftime("%Y-%m-%dT%H:%M:%S", v_datetime)
                v_params['Item'].update({ myTable_2_Params[2]: v_rangeKey })
            elif tag.startswith('EXIF'):
                exif_tag_str = tag.lstrip('EXIF')
                v_params['Item'].update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
                exifs_arr.update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
            else:
                v_params['Item'].update({ tag: exif_tags[tag].printable })
                exifs_arr.update({ tag: exif_tags[tag].printable })

            #print(v_params)
            v_ddb = boto3.resource('dynamodb', myRegion)
            v_ddb_table = v_ddb.Table(myTable_2_Params[0])

            v_ddb_table.put_item(**v_params)

    return exifs_arr

# ===============================================================
# Function for discovering image labels with AWS Rekognition
# ISO datetime format: YYYY-MM-DDThh:mm:ss.sTZD (eg 1997-07-16T19:20:30.45+01:00)
# iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", tuple_time)
# ===============================================================
def discoverImageLabels(bucket, image):
    # Uses AWS Rekognition to detect labels in photos
    # Writes all found to DynamoDB
    # ToDo:

    try:
        v_response = v_rek_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': image,
                },
            },
            MaxLabels=10,
            MinConfidence=70,
        )
        #Debug
        #print(v_response)

        v_ddb = boto3.resource('dynamodb', myRegion)
        v_ddb_table = v_ddb.Table(myTable_1_Params[0])

        v_iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

        v_return_labels = []

        for i_list in v_response['Labels']:
            v_ddb_table.put_item(
                Item={
                    myTable_1_Params[1]: image,
                    myTable_1_Params[2]: i_list['Name'],
                    'RkLblConfidence': int(i_list['Confidence']),
                    'DiscoveryDate': v_iso_time
                    }
                )
            v_return_labels.append({'Name' : i_list['Name'], 'Confidence': int(i_list['Confidence'])})

    except Exception:
        pass

    return v_return_labels

# *************************************************************************
# Creating local JSON file with data to be used on client side
# ToDo: Save on S3 bucket instead of local file
#
# *************************************************************************
def updateJSONconfig(bucket, image, labels, exiftags):

    Image = {
        'FileName' : image,
        'UploadTimeStamp' : time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        'EXIF_Tags' : exiftags,
        'RkLabels' : labels
    }

    v_ddb = boto3.resource('dynamodb', myRegion)
    v_ddb_table = v_ddb.Table(myTable_4_Params[0])

    v_ddb_table.put_item(
        Item=Image
    )

    # Full DB scan to pull updated data
    resp = v_ddb_table.scan(
        Select="ALL_ATTRIBUTES",
        )
    # List of images with all attributes pulled from DB for creating JSON config file
    imageT4Atrib = []
    for i in resp['Items']:
        imageT4Atrib.append(i)

    # Creating JSON config file in /tmp
    with open('/tmp/'+configFileJSON, 'wb') as cf_json:
        #print(simplejson.dumps(imageT4Atrib,cf_json, indent=4, separators=(',', ': ')))
        simplejson.dump(imageT4Atrib,cf_json)

    # Put JSON config file to target S3 bucket in ../js subfolder
    v_jsonConfigS3 = "v2/js/" + configFileJSON
    with open('/tmp/'+configFileJSON, 'rb') as cf_json:
        v_s3client.upload_fileobj(cf_json, bucket, v_jsonConfigS3)
