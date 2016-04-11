$(function () {

  var container = $('.rule-container');
  var conditions_container = $('#conditions-container');
  var actions_container = $('#actions-container');

  container.find('.values').select2({ width: '100%' });

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

  var updateRemove = function ($target) {
    $target.find('.rule').eq(0).removeClass('rule-border');
    $target.find('.rule-and').eq(0).removeClass('show').addClass('hide');
    if($target.find('.rule-remove').length == 1) {
      $target.find('.rule-remove').removeClass('show').addClass('hide');
    } else {
      $target.find('.rule-remove').addClass('show');
    }
  };

  $('.rule-add').on('click', function () {
    var $from = $($(this).data('from')),
        $to = $($(this).data('to')),
        form = $from.clone();
    form.removeClass('hide');
    $to.append(form);
    updatePrefix($to);
    updateRemove($to);
    form.find('select').trigger('change');
  });

  $('.rule-add-action').on('click', function () {
    actions_container.find('[data-disable-form]').hide();
  });

  container.on('click', '.rule-remove', function () {
    var $rule = $(this).parents('.rule'),
        $target = $rule.parents('.rule-container');
    $rule.fadeOut('fast', function () {
      $(this).remove();
      updatePrefix($target);
      updateRemove($target);
      if(actions_container.find('.rule').length == 1) {
        actions_container.find('[data-disable-form]').show();
      }
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

  updateRemove(conditions_container);
  updateRemove(actions_container);

  var conditions_height = conditions_container.parents('.panel').height();
  var actions_height = actions_container.parents('.panel').height();
  if(conditions_height > actions_height) {
    actions_container.parents('.panel').css('min-height', conditions_height);
    conditions_container.parents('.panel').css('min-height', conditions_height);
  } else {
    actions_container.parents('.panel').css('min-height', actions_height);
    conditions_container.parents('.panel').css('min-height', actions_height);
  }

  actions_container.on('change', '[data-disable-form] input', function() {
    if($(this).prop('checked')) {
      $('.rule-add-action').hide();
      actions_container.find('[data-prop] input').prop('disabled', true);
    } else {
      $('.rule-add-action').show();
      actions_container.find('[data-prop] input').prop('disabled', false);
    }
  });
  actions_container.find('[data-disable-form] input').change();
});
