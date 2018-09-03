# AS3-PIG
The name stands for Amazon S3 Photo Intelligent Gallery

Project goal: let AWS S3 users to create searchable photogallery of images stored in a specific bucket. 

Approach: By triggering AWS Lambda function for uploaded images, service extracts EXIF meta data and detects list of objects with AWS Rekognition. All image properties can be used independepnty or in arbitrary combination to search for specific image. 
