$(function () {

  var container = $('.rule-container');
  var conditions_container = $('#conditions-container');
  container.find('.select').select2({ width: '100%' });

  var updatePrefix = function ($target) {
    $target.find('.rule').each(function (i) {
      $(this).find(':input').each(function () {
        var $input = $(this),
            _id = $input.attr('id');
        if(_id) {
          _id = _id.replace(/\d+/, i);
          var $label = $input.parents('.form-group').find('label');
          $input.attr('id', _id).attr('name', _id);
          $label.attr('for', _id);
        }
      });
    });
  };

  $('.rule-add').on('click', function () {
    var $from = $($(this).data('from')),
        $to = $($(this).data('to')),
        form = $from.clone();
    form.removeClass('hide');
    $to.append(form);
    updatePrefix($to, $from);
    form.find('select').trigger('change');
  });

  container.on('click', '.rule-remove', function () {
    var $rule = $(this).parents('.rule'),
        $target = $rule.parents('.rule-container');
    $rule.fadeOut('fast', function () {
      $(this).remove();
      updatePrefix($target);
    });
  });

  // conditions events
  conditions_container.on('change', '.field', function () {
    var url = conditions_container.data('url');
    var id = $(this).val();
    var condition = $(this).parents('.rule');

    $.get(url, {'id': id}, function (resp) {
      var dataset = $.map(resp.data, function (item) {
        return {'id': item[0], 'text': item[1]};
      });
      var select = condition.find('.values');
      select.find('option').remove();
      select.select2({ data: dataset, width: '100%' });
    });
  });

  conditions_container.find('.field').change();

});
