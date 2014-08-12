$(function () {

    $(".autosize").autosize();

    $(".select").select2();

    $("[data-toggle=delete]").on("click", function () {
        var msg = $(this).data("message");
        if (confirm(msg)) {
            var url = $(this).data("href");
            $.ajax({
                type: "DELETE",
                url: url,
                success: function (resp) {
                    if(resp.status == "success") {
                        window.location.replace(resp.url);
                    }
                    else if(resp.status == "error") {
                        alert(resp.message);
                    }
                }
            });
        }
    });

    var image_widget = $('.image-widget');

    if(image_widget.length > 0){

        image_widget.find('.image-upload').fileupload({

            dataType: 'json',

            add: function (e, resp) {
                var parent = $(resp.form).parents('.image-widget');
                parent.find('.loading').removeClass('hide');
                resp.submit();
            },

            done: function (e, resp) {
                var parent = $(resp.form).parents('.image-widget');
                parent.find('.image-container').html(resp.result.html);
                parent.find('.text-danger').text('');
            },

            fail: function (e, resp) {
                var parent = $(resp.form).parents('.image-widget');
                if(resp.jqXHR.status == 413) {
                    parent.find('.text-danger').text(
                        'File too large. Please upload files smaller than 1MB');
                } else {
                    var data = resp.jqXHR.responseJSON;
                    $.each(data, function (k, v) {
                        parent.find('.text-danger').text(v[0]);
                    });
                }

            },

            always: function (e, resp) {
                var parent = $(resp.form).parents('.image-widget');
                parent.find('.loading').addClass('hide');
            }

        });

        image_widget.on('click', '.change-photo', function () {
            var parent = $(this).parents('.image-widget');
            parent.find('.fileinput').toggleClass('hide');
        });

        image_widget.on('click', '.remove-photo', function () {
            var parent = $(this).parents('.image-widget');
            var msg = $(this).data('message');
            var url = $(this).data('url');
            if(confirm(msg)) {
                $.ajax({ url: url, type: 'DELETE' }).done(function (resp) {
                    parent.find('.image-container').fadeOut('fast');
                });
            }
        });

        image_widget.on('click', '.rotate-photo', function () {
            var url = $(this).data('url');
            var parent = $(this).parents('.image-widget');
            $.ajax({
                url: url, type: 'POST', dataType: 'json'
            }).done(function (data) {
                parent.find('.image-container').html(data.html);
                parent.find('.text-danger').text('');
            }).fail(function (data) {
                alert('Rotate failed.');
            });
        });

    }

    $('a[rel=fancybox]').fancybox({
        openEffect  : 'elastic',
        closeEffect : 'elastic'
    });

});
