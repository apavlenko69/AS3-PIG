"""AS3 Photo Index Gallery """

import boto3
import json
import datetime
import exifread as exif

MY_REGION = 'eu-west-1'
JSON_CONFIG_FILE = 'pigconfig.json'
REKOGNITION_IMG_SIZE_LIMIT = 15*1024*1024  # Check AWS limitations

# lambda_client = boto3.client('lambda')

print('Loading function')


def detect_rk_labels(image, s3bucket):
    """
    Function for discovering image labels with AWS Rekognition.

    :param image: S3 object key for uploaded image file
    :param s3bucket: S3 bucket with image

    returns: dictionary of detected labels with probability numbers
    """

    try:
        rk_client = boto3.client('rekognition', region_name=MY_REGION)

        labels = []

        resp = rk_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': s3bucket,
                    'Name': image,
                    },
                },
            MaxLabels=3,
            MinConfidence=70,
        )

        for i_list in resp['Labels']:
            labels.append({'Name': i_list['Name'], 'Confidence': int(i_list['Confidence'])})

        return labels

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

    s3client = boto3.client('s3', region_name=MY_REGION)

    useful_exif_tags = [  # List of useful EXIF tags
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
                    shoot_date = datetime.datetime.strptime(exif_tags[tag].printable, "%Y:%m:%d %H:%M:%S").isoformat()
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


def create_pig_config(image, s3bucket, lbls, etags):
    """ Creates new gallery JSON config with image attributes """

    try:
        config_file_temp_path = '/tmp/' + JSON_CONFIG_FILE
        config_file_bucket_key = 'js/' + JSON_CONFIG_FILE  # Rebuild to avoid hardcoded path to config

        s3_client = boto3.client('s3', region_name=MY_REGION)

        img_attributes = {}

        img_attributes['FileName'] = image
        img_attributes['UploadTime'] = s3_client.get_object(Bucket=s3bucket, Key=image)['LastModified'].isoformat()

        img_attributes['RkLabels'] = lbls
        img_attributes['EXIF_Tags'] = etags

        list_of_photos = [img_attributes]

        with open(config_file_temp_path, 'w') as jfw:  # Writes file to Lambda instance folder /tmp
            json.dump(list_of_photos, jfw, indent=4)

        with open(config_file_temp_path, 'rb') as content:
            s3_client.upload_fileobj(content, s3bucket, config_file_bucket_key)
            print("Fresh config file {} created".format(config_file_bucket_key))

    except Exception as e:
        print('Error while writing JSON file: ', e)


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


def update_pig_config(image, s3bucket, lbls, etags):
    """
    Updates image attributes to gallery JSON config

    :param image: S3 object key for uploaded image
    :param s3bucket: name of the bucket
    :param lbls: list of detected Rekognition labels
    :param etags: dict of fetched EXIF tags

    :return: None. Updated config file, log entries
    """

    try:
        config_file_temp_path = '/tmp/' + JSON_CONFIG_FILE
        config_file_bucket_key = 'js/' + JSON_CONFIG_FILE  # Rebuild to avoid hardcoded path to config

        s3_client = boto3.client('s3', region_name=MY_REGION)

        if not is_key_exists(s3_client, s3bucket, config_file_bucket_key):
            create_pig_config(image, s3bucket, lbls, etags)

        with open(config_file_temp_path, 'wb') as data:  # Download pigconfig.json from S3 to Lambda /tmp
            s3_client.download_fileobj(s3bucket, config_file_bucket_key, data)

        with open(config_file_temp_path, 'r') as file:  # Read JSON structure
            json_object = json.load(file)

        for item in json_object:
            if not item['FileName'] == image:  # No duplicate entries found

                img_attributes = {}

                img_attributes['FileName'] = image
                img_attributes['UploadTime'] = s3_client.get_object(Bucket=s3bucket,
                                                                    Key=image)['LastModified'].isoformat()

                img_attributes['RkLabels'] = lbls
                img_attributes['EXIF_Tags'] = etags

                list_of_photos = json_object + [img_attributes]

                with open(config_file_temp_path, 'w') as jfw:  # Updates pigconfig.json in Lambda /tmp
                    json.dump(list_of_photos, jfw, indent=4)

                with open(config_file_temp_path, 'rb') as content:  # Upload updated config back to S3 bucket
                    s3_client.upload_fileobj(content, s3bucket, config_file_bucket_key)
            else:
                print("Update SKIPPED: object {} found in config file ".format(image))

    except Exception as e:
        print('Error while writing JSON file: ', e)


def lambda_handler(event, context):
    """
    Lambda handler function runs once trigger is activated by configured event.
    Detailed configuration is in app SAM template.
    """

    try:
        s3objkey = event['Records'][0]['s3']['object']['key']
        bucket = event['Records'][0]['s3']['bucket']['name']
        # event_time = event['Records'][0]['eventTime']

        print("\nDealing with <- {} -> image from album [- {} -]".format(str(s3objkey).split('/')[-1],
                                                                         str(s3objkey).split('/')[-2]))

        lbls = detect_rk_labels(s3objkey, bucket)
        exiftags = fetch_exif_tags(s3objkey, bucket)
        update_pig_config(s3objkey, bucket, lbls, exiftags)

        print("\nTime remaining (MS): {}\n".format(context.get_remaining_time_in_millis()))

    except Exception as e:
        print('ERROR: ', e)
