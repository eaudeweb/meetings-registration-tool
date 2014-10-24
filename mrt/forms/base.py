from itertools import groupby

from flask import request
from werkzeug import MultiDict

from wtforms import widgets, fields
from wtforms.widgets.core import html_params, HTMLString
from wtforms_alchemy import ModelForm

from mrt.models import db, Translation


class BaseForm(ModelForm):

    @classmethod
    def get_session(self):
        return db.session

    def __init__(self, formdata=None, obj=None, **kwargs):
        formdata = formdata.copy() if formdata else MultiDict()
        if request.form and not len(formdata):
            formdata.update(request.form)
        if request.files:
            formdata.update(request.files)
        super(BaseForm, self).__init__(formdata=formdata, obj=obj, **kwargs)
        self.obj = obj


class TranslationInputForm(BaseForm):

    class Meta:
        model = Translation
        field_args = {
            'english': {
                'widget': widgets.TextInput()
            },
            'french': {
                'widget': widgets.TextInput()
            },
            'spanish': {
                'widget': widgets.TextInput()
            }
        }


class DescriptionInputForm(BaseForm):

    class Meta:
        model = Translation
        field_args = {
            'english': {
                'widget': widgets.TextArea()
            },
            'french': {
                'widget': widgets.TextArea()
            },
            'spanish': {
                'widget': widgets.TextArea()
            }
        }


class BooleanField(fields.BooleanField):

    def process_data(self, data):
        self.data = True if data == 'true' else False


class MultiCheckboxField(fields.SelectMultipleField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

    def process_data(self, data):
        data = data or {}
        try:
            self.data = [setting for setting in data if data[setting]]
        except TypeError:
            raise TypeError('Parameter data must be a dict')

    def process_formdata(self, valuelist):
        self.data = {setting: True for setting in valuelist}


class CategoryWidget(widgets.ListWidget):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.pop('placeholder', None)
        class_ = kwargs.get('class_', '') + ' list-unstyled'
        kwargs['class_'] = class_
        html = ['<%s %s>' % (self.html_tag, html_params(**kwargs))]
        fields = groupby([opt for opt in field],
                         lambda x: x.label.text.group.code)
        for group, subfields in fields:
            for subfield in subfields:
                label = subfield.label.text
                html.append('<li><label>%s %s</label></li>' % (subfield(), label))
            html.append('<li class="separator"></li>')

        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class CategoryField(fields.RadioField):

    widget = CategoryWidget()
