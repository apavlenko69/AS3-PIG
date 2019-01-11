# AS3-PIG
The name is an acronym made from Amazon S3 Photo Index Gallery.

## Project goal
To build searchable photo gallery for images stored in a specific AWS S3 bucket. Images labeling is automated by AS3-PIG service. With images labeled by the service, and access provided with S3 web hosting, they can be found in on-line gallery using any of the following parameters: pre-selected EXIF tags, detected objects, file name or name of the containing folder, considered as an album. 

## Approach
To make use of service as simple as possible, it is enough just to upload images into AWS S3 bucket, configured for use with the gallery. This can be done using any of available options for images upload: S3 Management web console, aws cli or any third party software capable to work with S3 bucket. Any changes within bucket - uploading, removing, renaming images will be processed by the gallery, thus maintaining updated and consistent gallery configuration. AS3-PIG own front-end is a single page application (SPA), which can be replaced with other similar SPA options capable to work with JSON gallery config (out of service scope).

## Installation
Deployment of AS3-PIG service from Serverless Marketplace will build all required components (NOT YET IMPLEMENTED!). During deployment static web hosting and required policy are configured for all service components.

## Demo
http://as3-pig.s3-website-eu-west-1.amazonaws.com
