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
            add: function (e, data) {
                image_widget.find('.loading').removeClass('hide');
                data.submit();
            },
            done: function (e, data) {
                image_widget.find('.image-container').html(data.result.html);
                image_widget.find('.text-danger').text('');
            },
            fail: function (e, data) {
                var data = data.jqXHR.responseJSON;
                $.each(data, function (k, v) {
                    $('#' + k).next('.text-danger').text(v[0]);
                });
            },
            always: function (e, data) {
                image_widget.find('.loading').addClass('hide');
            }
        });

        image_widget.on('click', '.change-photo', function () {
            image_widget.find('.fileinput').toggleClass('hide');
        });

        image_widget.on('click', '.remove-photo', function () {
            var msg = $(this).data('message');
            var url = $(this).data('url');
            if(confirm(msg)) {
                $.ajax({ url: url, type: 'DELETE' }).done(function (resp) {
                    image_widget.find('.image-container').fadeOut('fast');
                });
            }
        });
    }

    $('a[rel=fancybox]').fancybox({
        openEffect  : 'elastic',
        closeEffect : 'elastic'
    });

});
