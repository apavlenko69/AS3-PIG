# AS3-PIG
The name is an acronym made from Amazon S3 Photo Intelligent Gallery.

Project goal: built searchable photogallery of images stored in a specific AWS S3 bucket. 

Approach: By triggering AWS Lambda function for uploaded images, service extracts EXIF meta data and detects list of objects with AWS Rekognition. All image properties can be used independenty or in arbitrary combination to search for specific image. 
