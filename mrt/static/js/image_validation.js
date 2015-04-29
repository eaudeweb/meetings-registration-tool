$(function () {

  // image upload validation
  var allowedExtensions = ['jpg', 'jpe', 'jpeg', 'png', 'gif', 'svg', 'bmp'];
  var maxUploadSize = $('#max-upload-size').data('bytes');
  var maxUploadSizeMB = Math.floor(maxUploadSize / (1024 * 1024));
  var fileInputs = $('[data-type=image]').find('input');

  // initialize array for storing file size for each input[type=file]
  // on page (initially 0)
  var fileSizes = [];
  for(var i=0; i<fileInputs.length; i++) {
    fileSizes.push(0);
  }

  // resets file input value without losing bound events
  function resetFormElement(element) {
    element.wrap('<form>').closest('form').get(0).reset();
    element.unwrap();
  }

  function removeErrors(element) {
    element.parents('.form-group').removeClass('has-error');
    element.parents('.file-field-container').siblings('.text-danger').remove();
  }

  function displayErrors(element, errorMessage) {
    var error_div = '<div class="text-danger"><small>' + errorMessage + '</small></div>';
    element.parents('.form-group').addClass('has-error');
    element.parents('.file-field-container').after(error_div);
  }

  fileInputs.on('change', function() {
      var file = this.files[0];
      var fileExtension = file.name.split('.').pop();
      var message;

      // index of current file input
      var inputIdx = fileInputs.index($(this));

      // update file size in file sizes array
      fileSizes[inputIdx] = file.size;

      // calculate sum of values in file sizes array
      var totalUploadSize = fileSizes.reduce(function (a, b) {return a + b});

      if (allowedExtensions.indexOf(fileExtension) == -1) {
        message = file.name + ' is not in the allowed extensions: ' + allowedExtensions.join(', ');
      }
      else if (file.size >= 1024 * 1024) {
        message = file.name + ' exceeds the maximum upload size (' + maxUploadSizeMB + 'MB)';
      }
      else if (totalUploadSize >= maxUploadSize) {
        message = 'Maximum upload size (' + maxUploadSizeMB + 'MB) has been exceeded';
      }
      else {
        removeErrors($(this));
      }

      if (message) {
        // remove errors belonging to previously uploaded file (if any)
        removeErrors($(this));

        // display errors for the current file
        displayErrors($(this), message);

        // reset file input (reset value property)
        resetFormElement($(this));

        // set file size to 0, as the upload is unsuccessful
        fileSizes[inputIdx] = 0;
      }
    });
});
