
$(function () {

    var handleChangeConditionField = function (data) {
        var condition = true;
        $.each(data, function (k, v) {
            var $item = $('[name=' + k + ']');
            var val = $item.val();

            if($item.is(':radio')) {
                val = $item.filter(':checked').val();
            }
            if($item.is(':checkbox')) {
                val = $item.filter(':checked').val();
                val = (val == 'y') ? 'true' : 'false';
            }

            if($.inArray(val, v) < 0) {
                condition = false;
            }
        });

        if(condition) {
            $(this).parents('.form-group').show();
        } else {
            $(this).parents('.form-group').hide();
        }
    };

    var fields = $(document).find('[data-rules]');
    fields.parents('.form-group').hide();

    fields.each(function (i, field) {
        var data = $(field).data('rules');
        $.each(data, function (k, v) {
            $('#' + k).on('change', function () {
                handleChangeConditionField.bind(field)(data);
            }).change();
        });
    });

});

