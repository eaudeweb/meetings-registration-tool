$(function () {

    $(".autosize").autosize();

    $(".select").select2({width: 'resolve'});

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
                    if(resp.status == "error") {
                        alert(resp.message);
                    }
                }
            });
        }
    });

    $("[data-toggle=restore]").on("click", function () {
        var msg = $(this).data("message");
        if (confirm(msg)) {
            var url = $(this).data("href");
            $.ajax({
                type: "POST",
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
                parent.find('.image-container').fadeIn('fast');
                parent.find('.text-danger').text('');
                parent.find('button').removeClass('disabled')
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
                    if(resp.status == "success") {
                        window.location.replace(resp.url);
                    }
                    parent.find('.image-container').fadeOut('fast');
                    parent.find('button').not('.change-photo').addClass('disabled');
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

        image_widget.on('click', '.crop-photo', function () {
            window.location.href = $(this).data('url');
        });

    }

    $('a[rel=fancybox]').fancybox({
        openEffect  : 'elastic',
        closeEffect : 'elastic'
    });

    var fixHelper = function(e, ui) {
        ui.children().each(function() {
            $(this).width($(this).width());
        });
        return ui;
    };

    var update = function (e, ui) {
        var data = $(this).sortable('serialize');
        var url = $(this).parents('table').data('url');
        $.post(url, data);
    };

    $('.sortable tbody').sortable({
        handle: ".handler",
        axis: "y",
        placeholder: "ui-state-highlight",
        update: update,
        helper: fixHelper
    });

    var search_participant = $('#search-participant');
    var search_participant_empty_template = [
        '<div class="tt-suggestion">',
        '<small><em>No participants found</em></small>',
        '</div>'
    ].join('\n');
    var searchSelected = function (e, suggestion, name) {
        if(suggestion && suggestion.url) {
            window.location.href = suggestion.url;
        }
    }
    var search = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: search_participant.attr('action') + '?search=%QUERY'
    });
    search.initialize();
    search_participant.find('input').typeahead(null, {
        name: 'search',
        displayKey: 'value',
        source: search.ttAdapter(),
        templates: {
            empty: search_participant_empty_template
        }
    }).on('typeahead:selected', searchSelected);


    $('[data-toggle=tooltip]').tooltip();

    // datatables default settings
    $.extend($.fn.dataTable.defaults, {
        'language': {
            'processing': '<img src="/static/images/ajax.gif" width=16 height=16>'
        }
    });
    $.extend($.fn.dataTable.ext.classes, {
        'sProcessing': 'dataTables_processing_mrt'
    });

});
