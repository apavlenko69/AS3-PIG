"""
    AS3 Photo Index Gallery
    Lambda function invokes for uploaded/updated/renamed images
"""

import boto3
import json
import datetime
import exifread as exif
import simplejson
import urllib.parse


AWS_REGION = ''  # Specific value to be assigned in Lambda handler from Event parameter-object
JSON_CONFIG_FILE = 'pigconfig.json'  # Gallery configuration file name
CONFIG_FILE_TEMP_PATH = '/tmp/' + JSON_CONFIG_FILE  # /tmp is the only writable in Lambda
CONFIG_FILE_BUCKET_KEY = 'js/' + JSON_CONFIG_FILE  #
DDB_TABLE = 'S3PigImageAttributes'  # Value MUST be the same as in SAM YAML template


print('Loading function')


def detect_rk_labels(image, img_size, s3bucket):
    """
    Function for discovering image labels with AWS Rekognition.

    :param image: S3 object key for uploaded image file
    :param img_size: size of the image
    :param s3bucket: S3 bucket with image

    returns: dictionary of detected labels with probability numbers

    Todo:
        - Skip processing of images exceeding Rekognition limits:
            * The minimum pixel resolution for height and width is 80 pixels
            * The Maximum images size as raw bytes passed in as parameter to an API is 5 MB.
    """

    accepted_image_types = ['jpg', 'JPG', 'png', 'PNG']
    rekognition_img_size_limit = 15 * 1024 * 1024

    try:
        if str(image).split('/')[-1].split('.')[-1] in accepted_image_types \
                and float(img_size) < rekognition_img_size_limit:

            rk_client = boto3.client('rekognition', region_name=AWS_REGION)

            labels = []

            resp = rk_client.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': s3bucket,
                        'Name': image,
                        },
                    },
                MaxLabels=5,
                MinConfidence=80,
            )

            for i_list in resp['Labels']:
                labels.append({'Name': i_list['Name'], 'Confidence': int(i_list['Confidence'])})

            return labels
        else:
            print("Labels detection skipped for {} because of service constraints violation".format(image))

    except Exception as e:
        print("Rekognition labels detection skipped because of the following error: ", e)
        pass


def fetch_exif_tags(image, s3bucket):
    """
    Function for detecting predefined, limited list of image EXIF tags.

    :param image: S3 object key for uploaded image file
    :param s3bucket: S3 bucket with image

    :return: dictionary of selected EXIF tags
    """

    s3client = boto3.client('s3', region_name=AWS_REGION)

    useful_exif_tags = [  # List of useful EXIF tags as presented in ExifRead
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
        'GPS GPSLongitudeRef',
        ]

    try:
        with open('/tmp/tmpimage.jpg', 'wb') as data:
            s3client.download_fileobj(s3bucket, image, data)

        tf = open('/tmp/tmpimage.jpg', 'rb')
        exif_tags = exif.process_file(tf, details=False)

        exifs_dict = {}

        for tag in exif_tags.keys():
            if tag in useful_exif_tags:  # Filtering whole EXIF array to select only list of useful

                if tag == 'Image DateTime':  # Creating datetime in ISO format
                    shoot_date = datetime.datetime.strptime(exif_tags[tag].printable,
                                                            "%Y:%m:%d %H:%M:%S").isoformat()
                    exifs_dict.update({'ShootingTime': shoot_date})

                elif tag.startswith('EXIF'):
                    exif_tag_str = tag.lstrip('EXIF')
                    exifs_dict.update({exif_tag_str.lstrip(): exif_tags[tag].printable})

                elif tag.startswith('GPS'):
                    exif_tag_str = tag.lstrip('GPS')
                    exifs_dict.update({exif_tag_str.lstrip(): exif_tags[tag].printable})

                else:
                    exifs_dict.update({tag: exif_tags[tag].printable})

        return exifs_dict

    except Exception as e:
        print("EXIF tags fetching failed because of : ", e)


def is_key_exists(client, bucket, key):
    """
    Checks presence of object in S3 bucket

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


def update_pig_config_ddb(image, s3bucket, lbls, etags):
    """
    Updates image attributes to gallery JSON config handled through DynamoDB

    :param image: S3 object key for uploaded image
    :param s3bucket: name of the bucket
    :param lbls: list of detected Rekognition labels
    :param etags: dict of fetched EXIF tags

    :return: None. Updated config file, log entries
    """

    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        ddb_table = boto3.resource('dynamodb', region_name=AWS_REGION).Table(DDB_TABLE)

        if ddb_table.table_status == 'ACTIVE':  # DynamoDB table exists and ready

            img_attributes = {}

            img_attributes['FileName'] = image
            img_attributes['UploadTime'] = s3_client.get_object(Bucket=s3bucket,
                                                                Key=image)['LastModified'].isoformat()

            img_attributes['RkLabels'] = lbls
            img_attributes['EXIF_Tags'] = etags

            ddb_table.put_item(Item=img_attributes)
            ddb_reply = ddb_table.scan(Select="ALL_ATTRIBUTES")  # Full DB scan to pull updated data
            list_of_photos = [i for i in ddb_reply['Items']]

            with open(CONFIG_FILE_TEMP_PATH, 'w') as jfw:  # Updates gallery config json in Lambda /tmp
                simplejson.dump(list_of_photos, jfw, indent=4)

            with open(CONFIG_FILE_TEMP_PATH, 'rb') as content:  # Upload updated config back to S3 bucket
                s3_client.upload_fileobj(content, s3bucket, CONFIG_FILE_BUCKET_KEY)

        else:
            print("Error: DynamoDB table resource was not available")

    except Exception as e:
        print('Error while writing JSON file: ', e)


def lambda_handler(event, context):
    """
    Lambda handler function runs once trigger is activated by configured event.

    Todo:
        Custom exception: check if identical image was already processed to avoid unnecessary charges
    """

    try:

        global AWS_REGION

        AWS_REGION = event['Records'][0]['awsRegion']

        s3objkey = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        s3objsize = event['Records'][0]['s3']['object']['size']
        bucket = event['Records'][0]['s3']['bucket']['name']
        
        print("\nDealing with <- {} -> image from album [- {} -]".format(str(s3objkey).split('/')[-1],
                                                                         str(s3objkey).split('/')[-2]))

        lbls = detect_rk_labels(s3objkey, s3objsize, bucket)
        exiftags = fetch_exif_tags(s3objkey, bucket)
        update_pig_config_ddb(s3objkey, bucket, lbls, exiftags)

        print("\nTime remaining (MS): {}\n".format(context.get_remaining_time_in_millis()))

    except Exception as e:
        print('ERROR: ', e)
