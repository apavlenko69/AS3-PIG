# AS3-PIG
The name is an acronym made from Amazon S3 Photo Index Gallery.

## Project goal
To build searchable photo gallery for images stored in the AWS S3 bucket. Images labeling is automated by AS3-PIG service. With images labeled by the service, and access provided with S3 web hosting, photographs can be found in on-line gallery using any of the following parameters: pre-selected EXIF tags, detected objects, file name or name of the containing folder, considered as an album. 

## Approach
To use service, it is enough just to upload images into AWS S3 bucket, configured for use with the gallery. This can be done using any of available options for files upload: S3 Management web console, aws cli or any third party software capable to work with S3 bucket. Any changes within bucket - uploading, removing, renaming images will be processed by the service, thus maintaining updated and consistent gallery configuration. AS3-PIG own front-end is a single page application (SPA), which can be replaced with other available SPA options, capable to work with JSON gallery config (out of service scope).

## Installation
Deployment of AS3-PIG service can be done with building AWS CludFormation stack with YAML template from this repository. During deployment all service components, including S3 bucket with web hosting, Lambda functions, DynamoDB table will be created. Also static files will be copied from git and customized for use with specific bucket and selected region. To start using gallery upload images into img/ folder of new bucket. Deployment tested with no issues for eu-west-1 (Ireland), us-east-1 (US East (N. Virginia)) and ap-northeast-1 (Tokyo).
### Procedure
If you have SAM CLI installed below script, populated with your vaiables, can be used for deployment from command line.

#!/bin/bash
PROJECT_PATH=~/AS3-PIG/app/
SAM_TEMPLATE=s3pig-template.yaml
BUILD_TEMPLATE=template.yaml
DEPLOY_TEMPLATE=d-template.yaml
BUILD_FOLDER=build/

AWS_REGION=[YOUR_AWS_REGION]
PACKAGE_BUCKET=[S3_BUCKET_IN YOUR_AWS_REGION]
STACK_NAME=[NAME_FOR_YOUR_CLOUD_FORMATION_STACK]

cd ${PROJECT_PATH}
sam validate -t ${SAM_TEMPLATE}

sam build \
    -t ${SAM_TEMPLATE} \
    -m requirements.txt \
    --use-container \
    --build-dir ${PROJECT_PATH}${BUILD_FOLDER} \

cd ${PROJECT_PATH}${BUILD_FOLDER}

sam package \
    --template-file ${BUILD_TEMPLATE} \
    --s3-bucket ${PACKAGE_BUCKET} \
    --s3-prefix build \
    --output-template-file ${DEPLOY_TEMPLATE}

sam deploy \
    --template-file ${DEPLOY_TEMPLATE} \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}


## Demo
http://as3-pig.s3-website-eu-west-1.amazonaws.com
