# ******************************************************************************
#  ! For Python version 3 !
#
#  This script is a main component of install procedure for AS3-PIG service.
#  AWS region and bucket name are mandatory input parameters for execution.
#  It must be safe to run script multiple times for the same bucket.
#
#  AS3-PIG service infrastructure will be created as result of running.
#  AS3-PIG service components and settings:
#   - DynamoDB tables for image attributes (Rekognition labels, exif tags)
#   - JSON config file with image attributes for web gallery frontend
#   - Static web site hosting on bucket with images (public access required)
#   - SPA file structure withing bucket (static web site)
#
#  ToDo:
#   1) Draw script algorithm
#   2) Follow PEP8, always check with pycodestyle
# ******************************************************************************

import boto3
import mimetypes


MY_REGION = 'eu-west-1'
MY_BUCKET = 'mpip'

# Allowed mime types
IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/gif',
    'image/png',
    'image/pjpeg',
    'image/bmp']

# JSON image attributes file
JSON_CONFIG_FILE = 'GalleryConfig.json'

# ============================================================
# Function for DynamoDb tables creation
# Function parameter is list of ['Table_Name', 'HASH', 'RANGE']
# ToDo: make separate procedures for Primary Key and composite key tables
# =============================================================


# ===============================================================
# Function for fetching Exif tags from image file
# ToDo: Is it possible to not download file?
# ===============================================================


# ===============================================================
# Function for discovering image labels with AWS Rekognition
# ISO datetime format: YYYY-MM-DDThh:mm:ss.sTZD
# (eg 1997-07-16T19:20:30.45+01:00)
# iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", tuple_time)
# ===============================================================


# *************************************************************************
# Creating local JSON file with data to be used on client side
# ToDo: Save on S3 bucket instead of local file
#
# *************************************************************************


# *************************************************************************
# Listing images in the bucket and for each found photo:
#   - discovering labels and saving to DynamoDB T1
#   - extracting Exif tags and saving to DynamoDB T2
#   - store consolidated data in T4 and create JSON config from it
# *************************************************************************


# ****************************
#       Start of actions
# ****************************
