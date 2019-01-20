"""
    AS3 Photo Index Gallery
    Lambda function invokes for uploaded/updated/renamed images
"""

import boto3
import json
import datetime
import exifread as exif
import piexif
from PIL import Image
import simplejson
import urllib.parse


AWS_REGION = ''  # Specific value to be assigned in Lambda handler from Event parameter-object
JSON_CONFIG_FILE = 'pigconfig.json'  # Gallery configuration file name
CONFIG_FILE_TEMP_PATH = '/tmp/' + JSON_CONFIG_FILE  # /tmp is the only writable in Lambda
CONFIG_FILE_BUCKET_KEY = 'js/' + JSON_CONFIG_FILE  #
DDB_TABLE = 'S3PigImageAttributes'  # Main part of value from SAM YAML template


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


def img_optimizer(image, s3bucket):
    """
    Optimizes JPEG file size

    :param image:
    :param s3bucket:
    :return:
    """
    try:
        s3client = boto3.client('s3', region_name=AWS_REGION)

        temp_ifile = '/tmp/tmp_ifile.jpg'

        with open(temp_ifile, 'wb') as data:
            s3client.download_fileobj(s3bucket, image, data)

        file_src = temp_ifile
        file_dst = file_src.split('.')[0] + '_.' + file_src.split('.')[1]

        img = Image.open(file_src)

        """
        Applying downsampling antialias algorithm without actual resize gives 30-40% lower file size. 
        Downsize with 0.97 aspect ratio gives 50% decrease. 
        """
        aspect = 0.97
        new_size = (int(float(img.size[0]) * float(aspect)), int(float(img.size[1]) * float(aspect)))

        new_img = img.resize(new_size, Image.ANTIALIAS)
        new_img.save(file_dst)
        piexif.transplant(file_src, file_dst)

        return 'SUCCESS', file_dst

    except Exception as err:
        print('Image optimization failed:', err)
        return 'FAILED', file_src


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
        # 'Image Orientation',
        'EXIF LensModel',
        'EXIF ISOSpeedRatings',
        'EXIF ExposureTime',
        'EXIF FNumber',
        'EXIF ExposureProgram',
        # 'EXIF ExposureMode'
        'EXIF FocalLength',
        # 'EXIF ExifImageWidth',
        # 'EXIF ExifImageLength',
        'GPS GPSAltitude',
        'GPS GPSLatitude',
        'GPS GPSLatitudeRef',
        'GPS GPSLongitude',
        'GPS GPSLongitudeRef',
        ]

    try:
        temp_file = '/tmp/tmpimage.jpg'

        with open(temp_file, 'wb') as data:
            s3client.download_fileobj(s3bucket, image, data)

        tf = open(temp_file, 'rb')
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


def update_pig_config_ddb(image, s3bucket, lbls=[], etags={}, ok='Yes', _json=True):
    """
    Updates image attributes to gallery JSON config handled through DynamoDB

    :param image: S3 object key for uploaded image
    :param s3bucket: name of the bucket
    :param lbls: list of detected Rekognition labels
    :param etags: dict of fetched EXIF tags
    :param ok: flag from "OptimizedSizeKey" DB item
    :param _json: flag to define if JSON config file should be updated as well

    :return: None. Updated config file, log entries
    """

    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)

        full_table_name = DDB_TABLE + '_' + s3bucket  # Allows multiple deployments under single AWS account
        ddb_table = boto3.resource('dynamodb', region_name=AWS_REGION).Table(full_table_name)

        if ddb_table.table_status == 'ACTIVE':  # DynamoDB table exists and ready

            img_attributes = {}

            img_attributes['FileName'] = image
            img_attributes['UploadTime'] = s3_client.get_object(Bucket=s3bucket,
                                                                Key=image)['LastModified'].isoformat()

            img_attributes['RkLabels'] = lbls
            img_attributes['EXIF_Tags'] = etags
            img_attributes['OptimizedSizeKey'] = ok

            ddb_table.put_item(Item=img_attributes)

            if json:
                ddb_reply = ddb_table.scan(Select="ALL_ATTRIBUTES")  # Full DB scan to pull updated data
                list_of_photos = [i for i in ddb_reply['Items']]

                with open(CONFIG_FILE_TEMP_PATH, 'w') as jfw:  # Updates gallery config json in Lambda /tmp
                    simplejson.dump(list_of_photos, jfw)

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

        full_table_name = DDB_TABLE + '_' + bucket
        ddb_table = boto3.resource('dynamodb', region_name=AWS_REGION).Table(full_table_name)

        resp = ddb_table.get_item(Key={'FileName': s3objkey})
        okey = resp.get('Item', {'OptimizedSizeKey': 'None'}).get('OptimizedSizeKey', 'No')

        if okey == 'Yes':  # In DB file marked as optimized

            lbls = detect_rk_labels(s3objkey, s3objsize, bucket)
            exiftags = fetch_exif_tags(s3objkey, bucket)
            update_pig_config_ddb(s3objkey, bucket, lbls, exiftags, okey)

        elif okey == 'No' or okey == 'None':  # file size is not optimized according to DB record

            _, optimized_img_path = img_optimizer(s3objkey, bucket)
            update_pig_config_ddb(s3objkey, bucket, ok='Yes', _json=False)

            # Now we can PUT optimized file from /tmp to bucket
            s3client = boto3.client('s3', region_name=AWS_REGION)
            with open(optimized_img_path, 'rb') as content:  # Upload optimized image to S3
                s3client.upload_fileobj(content, bucket, s3objkey)

            print("Image {} size was optimized and uploaded to bucket as {}".format(
                str(s3objkey).split('/')[-1], s3objkey))

        print("\nTime remaining (MS): {}\n".format(context.get_remaining_time_in_millis()))

    except Exception as e:
        print('ERROR: ', e)
