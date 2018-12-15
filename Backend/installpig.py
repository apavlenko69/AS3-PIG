#!~/anaconda3/bin/python36
"""
This code is for initial setup of AS3-PIG service, which is
Amazon S3 Photo Intelligent Gallery.

AWS region and bucket name are mandatory input parameters for execution.
It must be safe to run script multiple times for the same bucket.

AS3-PIG service infrastructure will be created as result of code execution.
AS3-PIG service components and required settings are:
   - DynamoDB tables for image attributes (detected Rekognition labels,
   exif tags, file name/attributes and containing folder);
   - JSON config file with image attributes - input for web gallery frontend;
   - Enabled static web site hosting on Amazon bucket containing images
     (public access required!);
   - SPA file structure withing bucket (static web site folders).
"""

# import boto3

MY_REGION = 'eu-west-1'
MY_BUCKET = 'as3-pig'

# Accepted image mime types
IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/gif',
    'image/png',
    'image/pjpeg',
    'image/bmp']

JSON_CONFIG_FILE = 'GalleryConfig.json'  # JSON image attributes config file

pig_table1_params = {
    't_name': 'T1_RkLabels',  # Review AWS documentation for DynamoDB keys
    't_hkey': 'S3ObjKey',
    't_rkey': 'RkLabel',
    }

pig_table2_params = {
    't_name': 'T2_ExifTags',
    't_hkey': 'S3ObjKey',
    't_rkey': 'ShootingDateTime',  # How to reserve search for additional exif fields: 'MakeIndex','Image_Make'?
    }

pig_table3_params = {
    't_name': 'T3_AllImgAttributes',
    't_hkey': 'S3ObjKey',
    't_rkey': 'ShootingDateTime',  # How to reserve search for additional exif fields: 'MakeIndex','Image_Make'?
    }

"""
pig_Table_2_Params = ['T2_ExifTags','S3ObjKey','ShootingDateTime','MakeIndex','Image_Make']
pig_Table_3_Params = ['T3_AllImgAttributes','FileName','UploadTimeStamp']
"""


def create_ddb_tables():
    """
    Function for AWS DynamoDb tables initial creation.

    :arg
        Dict of table parameters

    :returns
        Log record of tables creation.
        Log record to skip creation if tables exist already.
    """


def fetch_exif_tags():
    """
    Function for fetching Exif tags from uploaded image file

    :arg
        bucket, image

    :returns
        dictionary of extracted exif tags

    ToDo: Is it possible to not download file?
    """


def discover_rk_labels():
    """
    Function for discovering image labels with AWS Rekognition
    ISO datetime format: YYYY-MM-DDThh:mm:ss.sTZD

    :arg

    :returns

    """


def create_json_config():
    """
    Creating local JSON file with data to be used on client side

    :arg

    :returns

    """


def insert_images_data():
    """
    Paginates images in the bucket and for each photo does next:
    - discovers labels and saves to DynamoDB T1
    - extracts Exif tags and saves to DynamoDB T2
    - stores consolidated data in T3 and creates JSON config from it

    :arg

    :returns

    """

    print(__name__, 'does images processing with paginator')


if __name__ == '__main__':
    print("Successfully run as a script {f}".format(f=__name__))
