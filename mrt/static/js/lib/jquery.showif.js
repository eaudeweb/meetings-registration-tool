
$(function () {

    var handleChangeConditionField = function (rules, context) {
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

            if(context['mark_visible']) {
                if(condition) {
                    $(this).parents('.form-group').first().show();
                    return;
                } else {
                    $(this).parents('.form-group').first().hide();
                }
            }
            if(context['mark_disable_form']) {
                var form = $(this).parents('form');
                if(condition) {
                    var msg = $('<div>')
                        .attr({'class': 'alert alert-danger'})
                        .text('Registration form is disabled for this options');
                    form.before(msg);
                    form.find('button[type=submit]').prop('disabled', true);
                } else {
                    form.find('button[type=submit]').prop('disabled', false);
                }
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

        var context = {
            mark_visible: $(field).data('visible'),
            mark_disable_form: $(field).data('disable-form')
        };
        if(context['mark_visible'] || context['mark_disable_form']) {
            for(var i=0; i < keys.length; i++){
                $('#' + keys[i]).on('change', function () {
                    $.proxy(handleChangeConditionField, field)(rules, context);
                }).change();
            }
        }
    });

});

