# -*- coding: utf-8 -*-
# *********************************************************************************************
# Crawler module
# 1) Creates 3 tables: for discovered Rk labels (Table1), for extracted exif tags (Table2),
#   and all-in-one (Table4) for JSON config file
# 2) Fetches list of image objects in S3 bucket and for each photo does:
#   - AWS Rekognition: detects labels and writes results in scalars to Table 1
#   - exifread: downloads image, reads exif tags and writes subset of tags in scalars to Table2
#   - JSON config: keeps all attributes in one table and export its data/structure to JSON on S3
# version for python 3
#  ********************************************************************************************

from __future__ import print_function

import boto3
import exifread
import time
import urllib
import json, simplejson
import mimetypes

from boto3.dynamodb.conditions import Key, Attr

myRegion = 'eu-west-1'
myBucket = 'mpip'

# p[0] - table name, p[1] - HASH, p[2] - RANGE, p[3] - LocalIndexName, p[4] - Index sort key (or RANGE)
myTable_1_Params = ['T1_RkLabels','S3ObjKey','RkLabel']
myTable_2_Params = ['T2_ExifTags','S3ObjKey','ShootingDateTime','MakeIndex','Image_Make']
#myTable_3_Params = ['T3_Genres','S3ObjKey','Genre'] # reserved for genres information
myTable_4_Params = ['T4_AllImgAttributes','FileName','UploadTimeStamp']

# Allowed mime types
imageMimeTypes = [
'image/jpeg',
'image/gif',
'image/png',
'image/pjpeg',
'image/bmp'
]

v_s3client = boto3.client('s3')
v_rek_client = boto3.client('rekognition', region_name = myRegion)
v_ddb_client = boto3.client('dynamodb', region_name = myRegion)

# JSON structure with all image data for use on client side with JavaScript
configFileJSON = 'GalleryConfig.json'

# ============================================================
# Function for DynamoDb tables creation
# Function parameter is list of ['Table_Name', 'HASH', 'RANGE']
# ToDo: make separate procedures for Primary Key and composite key tables
# =============================================================
def createTable(tparams):
    tbl_list = v_ddb_client.list_tables()

    if tparams[0] not in tbl_list['TableNames']:
        if tparams[0] == 'T1_RkLabels':
            v_crtbl_params = {
                'TableName' : tparams[0],
                'KeySchema' : [
                    {
                        'AttributeName': tparams[1],
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': tparams[2],
                        'KeyType': 'RANGE'
                    }
                ],
                'AttributeDefinitions':[
                    {
                        'AttributeName': tparams[1],
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': tparams[2],
                        'AttributeType': 'S'
                    },
                ],
                'ProvisionedThroughput':{
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        elif tparams[0] == 'T4_AllImgAttributes':
            v_crtbl_params = {
                'TableName' : tparams[0],
                'KeySchema' : [
                    {
                        'AttributeName': tparams[1],
                        'KeyType': 'HASH'
                    }
                ],
                'AttributeDefinitions':[
                    {
                        'AttributeName': tparams[1],
                        'AttributeType': 'S'
                    }
                ],
                'ProvisionedThroughput':{
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        elif tparams[0] == 'T2_ExifTags':
            v_crtbl_params = {
                'TableName': tparams[0],
                'KeySchema': [
                    {
                        'AttributeName': tparams[1],
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': tparams[2],
                        'KeyType': 'RANGE'
                    },
                ],
                'LocalSecondaryIndexes': [
                    {
                        'IndexName': tparams[3],
                        'KeySchema': [
                            {
                                'AttributeName': tparams[1],
                                'KeyType': 'HASH',
                            },
                            {
                                'AttributeName': tparams[4],
                                'KeyType': 'RANGE'
                            },
                        ],
                        'Projection': {
                            'ProjectionType': 'KEYS_ONLY',
                        }
                    },
                ],
                'AttributeDefinitions':[
                    {
                        'AttributeName': tparams[1],
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': tparams[2],
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': tparams[4],
                        'AttributeType': 'S'
                    },
                ],
                'ProvisionedThroughput':{
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }

        v_ddb_table = v_ddb_client.create_table(**v_crtbl_params)
        waiter = v_ddb_client.get_waiter('table_exists')
        print('Info: Table', tparams[0], 'is being created... Please, be patient')

        waiter.wait(TableName=tparams[0])
        print('Info: Created table:', v_ddb_table['TableDescription']['TableName'])

    else:
        print('Info: Table', tparams[0], 'has been already created')

# ===============================================================
# Function for fetching Exif tags from image file
# ToDo: Is it possible to not download file?
# ===============================================================
def extractExifData(bucket, image):

    with open('/tmp/tmpimage.jpg', 'wb') as data:
        v_s3client.download_fileobj(bucket, image, data)

    tf = open('/tmp/tmpimage.jpg', 'rb')
    exif_tags = exifread.process_file(tf, details = False)

    exifs_arr = {}

    if (len(exif_tags) != 0):
        v_params = {
                'Item': {
                myTable_2_Params[1]: image,
                myTable_2_Params[2]: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) # default is today
                }
        }

        # List of useful EXIF tags
        v_useful_exif_tags = [
            'Image Make',
            'Image Model',
            'Image DateTime',
            'Image Orientation',
            'EXIF LensModel',
            'EXIF ISOSpeedRatings',
            'EXIF ExposureTime',
            'EXIF FNumber',
            'EXIF ExposureProgram',
            'EXIF ExposureMode'
            'EXIF FocalLength',
            'EXIF ExifImageWidth',
            'EXIF ExifImageLength',
            'GPS GPSAltitude',
            'GPS GPSLatitude',
            'GPS GPSLatitudeRef',
            'GPS GPSLongitude',
            'GPS GPSLongitudeRef'
            ]

        for tag in exif_tags.keys():
            # Filtering whole EXIF array to select only list of useful
            if tag in (v_useful_exif_tags):
            #if tag.startswith('Image'):

                if tag == 'Image DateTime':
                # Creating datetime in ISO format
                    v_datetime = time.strptime(exif_tags[tag].printable, "%Y:%m:%d %H:%M:%S")
                    v_rangeKey = time.strftime("%Y-%m-%dT%H:%M:%S", v_datetime)
                    v_params['Item'].update({ myTable_2_Params[2]: v_rangeKey })
                    exifs_arr.update({myTable_2_Params[2]: v_rangeKey})
                elif tag.startswith('EXIF'):
                    exif_tag_str = tag.lstrip('EXIF')
                    v_params['Item'].update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
                    exifs_arr.update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
                elif tag.startswith('GPS'):
                    exif_tag_str = tag.lstrip('GPS')
                    v_params['Item'].update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
                    exifs_arr.update({ exif_tag_str.lstrip(): exif_tags[tag].printable })
                else:
                    exif_tag_str = tag.replace(' ','_')
                    v_params['Item'].update({ exif_tag_str: exif_tags[tag].printable })
                    exifs_arr.update({ exif_tag_str: exif_tags[tag].printable })

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
    # ToDo: Add date of discovery to database

    v_return_labels = []

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

        # Face detection
        v_response2 = v_rek_client.detect_faces(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': image,
                },
            },
            Attributes='DEFAULT'
        )
        #Debug
        #print(v_response2)

        v_ddb = boto3.resource('dynamodb', myRegion)
        v_ddb_table = v_ddb.Table(myTable_1_Params[0])

        v_iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

        #v_return_labels = []
        #v_return_labels.append({'NumFacesDetected' : len(v_response2['FaceDetails'])})

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
def updateJSONconfig(image, uploadtimestamp, labels, exiftags):
    # Must have the same structure as DynamoDB table T4
    Image = {
        'FileName' : image,
        #'UploadTimeStamp' : time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        'UploadTimeStamp' : uploadtimestamp,
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
    with open('/tmp/'+configFileJSON, 'w') as cf_json:
        #print(simplejson.dumps(imageT4Atrib,cf_json, indent=4, separators=(',', ': ')))
        simplejson.dump(imageT4Atrib,cf_json, indent=4, separators=(',', ': '))

    # Put JSON config file to target S3 bucket in ../js subfolder
    v_jsonConfigS3 = "v2/js/" + configFileJSON
    with open('/tmp/'+configFileJSON, 'rb') as cf_json:
        v_s3client.upload_fileobj(cf_json, myBucket, v_jsonConfigS3)

# *************************************************************************
# Listing images in the bucket and for each found photo:
#   - discovering labels and saving to DynamoDB T1
#   - extracting Exif tags and saving to DynamoDB T2
#   - store consolidated data in T4 and create JSON config from it
# *************************************************************************
def addImagesData(bucket):
# Paginator allows to limit number of files to process with 'MaxItems'
    v_paginator_parameters = {
                    'Bucket': bucket,
                    'Prefix': 'v2/img',
                    'StartAfter': 'v2/img/',
                    'PaginationConfig': {'MaxItems': 5, 'PageSize': 100}
                    }

    v_paged_result = v_s3client.get_paginator('list_objects_v2').paginate(**v_paginator_parameters)
    i = 1
    for i_object in v_paged_result.search('Contents'):
        s3ObjKey = i_object['Key']
        s3ObjLastModified = i_object['LastModified'].strftime("%Y-%m-%dT%H:%M:%S")

        #if mimetypes.guess_type(s3ObjKey)[0] in imageMimeTypes:

        print('\nInfo:', i, '=====', s3ObjKey, '=====')
        v_labels = discoverImageLabels(bucket, s3ObjKey)
        v_tags = extractExifData(bucket, s3ObjKey)
        updateJSONconfig(s3ObjKey,s3ObjLastModified,v_labels,v_tags)
        #else:
        #    print('\nInfo:', '=====', s3ObjKey, 'skipped as it\'s not an image')
        #    i -= 1
        i += 1

# ****************************
#       Start of actions
# ****************************

# Checks if required DynamoDB tables created
createTable(myTable_1_Params) # for Labels
createTable(myTable_2_Params) # for EXIF tags
createTable(myTable_4_Params) # All_in_one for JSON config

# Crawles myBucket to find images and discover their attributes
addImagesData(myBucket)
