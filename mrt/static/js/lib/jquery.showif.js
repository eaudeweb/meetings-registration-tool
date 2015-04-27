
$(function () {

    var handleChangeConditionField = function (rules) {

        for(var i=0; i<rules.length; i++) {
            var data = rules[i],
                condition = true;

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
                $(this).parents('.form-group').first().show();
                return;
            } else {
                $(this).parents('.form-group').first().hide();
            }
        }

    };

    var fields = $(document).find('[data-rules]');
    fields.parents('.form-group').first().hide();

    fields.each(function (i, field) {
        var rules = $(field).data('rules');
        var keys = [];

        for(var i=0; i<rules.length; i++) {
            for(var k in rules[i]) {
                if($.inArray(k, keys)) {
                    keys.push(k);
                }
            }
        }

        for(var i=0; i<keys.length; i++){
            $('#' + keys[i]).on('change', function () {
                handleChangeConditionField.bind(field)(rules);
            });
        }

    });

});

