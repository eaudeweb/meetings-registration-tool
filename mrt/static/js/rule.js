$(function () {

  var conditions_container = $('#conditions-container');
  conditions_container.find('.select').select2({ width: '100%' });

  var updatePrefix = function () {
   conditions_container.find('.condition').each(function (i) {
      var field_label = 'conditions-' + i + '-field';
      var value_label = 'conditions-' + i + '-values';
      $(this).find('label').eq(0).attr('for', field_label);
      $(this).find('select').eq(0).attr('id', field_label)
             .attr('name', field_label)
      $(this).find('label').eq(1).attr('for', value_label);
      $(this).find('select').eq(1).attr('id', value_label)
             .attr('name', value_label)
    });
  };

  $('#condition-add').on('click', function () {
    var form = $('#default-condition-form').clone();
    form.removeClass('hide');
    conditions_container.append(form);
    updatePrefix();
    form.find('select').eq(0).trigger('change');
    form.find('select').eq(1).select2({ width: '100%' });
  });

 conditions_container.on('click', '.condition-remove', function () {
    $(this).parents('.condition').fadeOut('fast', function () {
      $(this).remove();
      updatePrefix();
    });
  });

  conditions_container.on('change', '.field', function () {
    var url = conditions_container.data('url');
    var id = $(this).val();
    var condition = $(this).parents('.condition');

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
