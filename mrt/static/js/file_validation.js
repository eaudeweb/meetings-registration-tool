$(function () {

  // file upload validation
  var allAllowedExtensions = {
      'image': ['jpg', 'jpe', 'jpeg', 'png', 'gif', 'svg', 'bmp'],
      'document': ['rtf', 'odf', 'ods', 'gnumeric', 'abw', 'doc', 'docx', 'xls', 'xlsx', 'pdf']
  };
  var maxUploadSize = $('#max-upload-size').data('bytes');
  var maxUploadSizeMB = Math.floor(maxUploadSize / (1024 * 1024));
  var maxFileSize = $('#max-file-size').data('bytes');
  var maxFileSizeMB = Math.floor(maxFileSize / (1024 * 1024));

  var fileInputs = $('input[type=file]');

  // initialize array for storing file size for each input[type=file]
  // on page (initially 0)
  var fileSizes = [];
  for (var i=0; i<fileInputs.length; i++) {
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

      var fileType = $(this).parent().attr('data-type');
      var allowedExtensions = allAllowedExtensions[fileType];

      // index of current file input
      var inputIdx = fileInputs.index($(this));

      // update file size in file sizes array
      fileSizes[inputIdx] = file.size;

      // calculate sum of values in file sizes array
      var totalUploadSize = fileSizes.reduce(function (a, b) {return a + b});

      if (allowedExtensions.indexOf(fileExtension.toLowerCase()) == -1) {
        message = file.name + ' is not in the allowed extensions: ' + allowedExtensions.join(', ');
      }
      else if (file.size >= maxFileSize) {
        message = file.name + ' exceeds the maximum file size (' + maxFileSizeMB + 'MB)';
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

  function updateCoords(c, name) {
    $('input[name=' + name + '_x1_]').val(c.x);
    $('input[name=' + name + '_y1_]').val(c.y);
    $('input[name=' + name + '_x2_]').val(c.x2);
    $('input[name=' + name + '_y2_]').val(c.y2);
    $('input[name=' + name + '_w_]').val(c.w);
    $('input[name=' + name + '_h_]').val(c.h);
  }

  function showPhotoCrop(event) {
    var name = event.target.name;
    var selectedFile = event.target.files[0];
    var reader = new FileReader();
    var photoSize = event.target.dataset.photosize.split('x');
    var minWidth = parseInt(photoSize[0]);
    var minHeight = parseInt(photoSize[1]);
    var ratio = minWidth / minHeight;

    var imgtag = document.getElementById("photo_" + name);
    var crop_div = document.getElementById('image_crop_' + name);

    if ($(imgtag).data('Jcrop')) {
      $(imgtag).data('Jcrop').destroy();
    }

    imgtag.title = selectedFile.name;

    reader.onload = function(event) {
      imgtag.src = event.target.result;
      crop_div.style.display = "inherit";

      $(imgtag).Jcrop({
        aspectRatio: ratio,
        minSize: [minWidth, minHeight],
        onChange: c => updateCoords(c, name),
        onSelect: c => updateCoords(c, name),
        boxWidth: 400,
      }, function () {
        // Set an optimal selection by default.
        var imageWidth = imgtag.width;
        var imageHeight = imgtag.height;
        var croppedWidth, croppedHeight;

        if (ratio <= 1) {
          croppedWidth = imageWidth / 2;
          croppedHeight = imageWidth / 2 / ratio;
        } else {
          croppedHeight = imageHeight / 2;
          croppedWidth = imageHeight / 2 * ratio;
        }

        this.animateTo([
          (imageWidth - croppedWidth) / 2,
          (imageHeight - croppedHeight) / 2,
          (imageWidth - croppedWidth) / 2 + croppedWidth,
          (imageHeight - croppedHeight) / 2 + croppedHeight,
        ]);
      });
    };
    reader.readAsDataURL(selectedFile);
  }

  document.querySelectorAll('[data-photosize]').forEach(
    el => el.addEventListener('change', showPhotoCrop)
  );
});
