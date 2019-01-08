# AS3-PIG
The name is an acronym made from Amazon S3 Photo Index Gallery.

## Project goal
To build searchable photogallery for images stored in a specific AWS S3 bucket. Images in gallery can be found using any of the following: EXIF tags, detected objects, file name or name of the containing folder, considered as an album. 

## Approach
To start using service images have to be uploaded into AWS S3 bucket, dedicated for use with the gallery, aka AS3-PIG. Available options for images upload are S3 Management web console, aws cli or any third party software capable to work with S3 bucket. Create or Remove bucket events trigger Lambda functions for: extracting image EXIF tags, detecting ojects, updating and maintaining gallery configuration. Static web hosting and required policy configured on S3 bucket to provide access to the gallery. S3-PIG front-end is a single page application (SPA). 

## Installation
Deployment of AS3-PIG service from Serverless Marketplace will build all required components (NOT YET IMPLEMENTED!). 

## Demo
http://as3-pig.s3-website-eu-west-1.amazonaws.com
