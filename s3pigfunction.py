"""AS3 Photo Index Gallery """

import boto3
import exifread as exif
import time

MY_REGION = 'eu-west-1'

lambda_client = boto3.client('lambda')

print('Loading function')


def detect_rk_labels(image, s3bucket):
    """
    Function for discovering image labels with AWS Rekognition.
    ISO datetime format: YYYY-MM-DDThh:mm:ss.sTZD

    :param image: S3 object key for uploaded image file
    :param s3bucket: S3 bucket with image

    returns: dictionary of detected labels with probability numbers
    """
    try:

        rk_client = boto3.client('Rekognition', region=MY_REGION)  # region

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
    Function for detecting predefined list of image EXIF tags

    :param image: S3 object key for uploaded image file
    :param s3bucket: S3 bucket with image

    :return: dictionary of EXIF tags
    """

    s3client = boto3.client('s3', region=MY_REGION)

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
            s3client.download_fileobj(s3bucket, image.decode('utf8'), data)

        tf = open('/tmp/tmpimage.jpg', 'rb')
        exif_tags = exif.process_file(tf, details=False)

        exifs_dict = dict

        for tag in exif_tags.keys():
            if tag in (useful_exif_tags): # Filtering whole EXIF array to select only list of useful
                if tag == 'Image DateTime':
                    # Creating datetime in ISO format
                    dt = time.strptime(exif_tags[tag].printable, "%Y:%m:%d %H:%M:%S")
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


def lambda_handler(event, context):
    """Lambda handler function runs once trigger is activated by configured event"""

    try:
        s3objkey = event['Records'][0]['s3']['object']['key']
        bucket = event['Records'][0]['s3']['bucket']['name']

        lbls = detect_rk_labels(s3objkey, bucket)
        exiftags = fetch_exif_tags(s3objkey, bucket)

        return lbls, exiftags

    except Exception as e:
        print('ERROR: ', e)
