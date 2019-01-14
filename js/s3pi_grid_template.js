// Creating module
angular.module('s3PIGrid', []);

// Referencing module
var s3pigrid = angular.module('s3PIGrid',['ngSanitize']);

//s3pigrid.config(function($compileProvider) {
//  $compileProvider.preAssignBindingsEnabled(true);
//});

// Gallery logic: fetching data from JSON
s3pigrid.controller('S3PIGalleryConfig', function($scope, $rootScope, $http, $sce) {
    $http.get('https://s3-<AWS-REGION>.amazonaws.com/<BUCKET-NAME>/js/pigconfig.json')
      .then(function onSuccess(response) {
        $scope.imagesData = response.data; // Object with whole gallery data
        $scope.totalp = response.data.length;  // Total number of photos in album

        // Returns number of Exif keys
        $scope.exif_len = function(obj){
          var i=0;
          for(p in obj) if(Object.prototype.hasOwnProperty.call(obj,p)){ i++ };
          return i;
        };

        // This function takes GPS tags in DMS text format and converts to DD array
        $scope.eGPStoDD = function(exif_obj) {
          if (exif_obj.hasOwnProperty("GPSLongitude")) {

            la = exif_obj.GPSLatitude.split(",");
            var la2 = la[2].slice(0,-1).split("/");
            var lat_array_string = la[0] + "," + la[1] + "," + la2[0] + "," + la2[1] + "]";

            lo = exif_obj.GPSLongitude.split(",");
            var lo2 = lo[2].slice(0,-1).split("/");
            var lon_array_string = lo[0] + "," + lo[1] + "," + lo2[0] + "," + lo2[1] + "]";

            var lat_array = JSON.parse(lat_array_string);
            var lon_array = JSON.parse(lon_array_string);

            var latitude = (lat_array[0] + lat_array[1]/60 + lat_array[2]/lat_array[3]/3600).toPrecision(8);
            if (exif_obj.GPSLatitudeRef === "S") {
              latitude = 0 - latitude;
            }

            var longitude = (lon_array[0] + lon_array[1]/60 + lon_array[2]/lon_array[3]/3600).toPrecision(8);
            if (exif_obj.GPSLongitudeRef === "W") {
              longitude = 0 - longitude;
            }

            $scope.coords = [];
            $scope.coords[0] = latitude;
            $scope.coords[1] = longitude;

            return $scope.coords;
          }
        };

        // Checks if GPS tags are present in config file
        $scope.hasgps = function(obj){
          if (obj.hasOwnProperty("GPSLongitude")) {
            return true;
          }
          else {
            return false;
          }
        }
      });

      // Invokes Google map embeded in iframe
      $scope.trustSrc = function(obj) {
        lat = $scope.eGPStoDD(obj)[0];
        lon = $scope.eGPStoDD(obj)[1];
        api_key = "AIzaSyDCBDh5PrbSC9G-m4G3NpQYjymApurLkCc";
        zoom_factor = 14;
        map_url = "https://www.google.com/maps/embed/v1/place?q=" + lat + "," + lon + "&zoom=" + zoom_factor + "&key=" + api_key;
        return $sce.trustAsResourceUrl(map_url);
      };

      // Returns image containing folder to use it as album name
      $scope.getImgFolder = function(obj) {
        var s3ObjKey = obj.FileName.split("/");
        var album_name = s3ObjKey[s3ObjKey.length - 2];
        return album_name;
      };

      // Gallery parameters
      $scope.myBucketURL = "https://s3-<AWS-REGION>.amazonaws.com/<BUCKET-NAME>/";
      //$scope.myBucketURL = $location.protocol() + '://' + $location.host();
      $scope.sresult = 0;   // Initial value for number of found photos
      $scope.cpage = 1;     // Default for current page #
      $scope.gstep = 3;     // Default for number of photos per page
      $scope.gstepMax = 20; // Max number of photos per page
      $scope.startFrom = 0; //Default value - start from first page

      //Sort order logic
      $scope.ordByList = ['-UploadTime','UploadTime','-EXIF_Tags.ShootingTime','EXIF_Tags.ShootingTime'];
      $scope.rvrs = false;
      $scope.ordBy = function(or_param){
        if (or_param) {
          return $scope.ordByList[or_param];
        }
        // Default selection for sort order
        else {
          return $scope.ordByList[0];
        }
      };

      // "+" and "-" buttons to change number of photos per page
      $scope.gstepchange = function(p_sign) {
        if (p_sign == 0 && $scope.gstep > 1) {
          $scope.gstep --;
        }
        else if (p_sign == 1 && $scope.gstep < $scope.gstepMax) {
          $scope.gstep ++;
        };
      };
});
