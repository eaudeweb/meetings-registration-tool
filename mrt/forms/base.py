from itertools import groupby

from flask import request, render_template
from flask import current_app as app
from werkzeug import MultiDict, FileStorage

from flask_wtf.file import FileField as _FileField
from sqlalchemy_utils import Country

from wtforms import widgets, fields
from wtforms.widgets.core import html_params, HTMLString
from wtforms_alchemy import ModelForm
from wtforms_alchemy import CountryField as _CountryField

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
        self.data = True if (data == 'true' or data is True) else False


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
                html.append('<li><label>%s %s</label></li>' % (
                    subfield(), label))
            html.append('<li class="separator"></li>')

        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class CategoryField(fields.RadioField):

    widget = CategoryWidget()


class CountryField(_CountryField):

    def process_data(self, value):
        if isinstance(value, Country):
            self.data = value if value.code else None
        else:
            self.data = value

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0]:
                self.data = self.coerce(valuelist[0])
            else:
                self.data = None

    def _get_choices(self):
        choices = super(CountryField, self)._get_choices()
        if not self.flags.required:
            choices = [('', '---')] + choices
        return choices


class FileInput(object):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        return HTMLString(render_template(
            'meetings/registration/_image_widget.html',
            field=field))


class FileField(_FileField):

    widget = FileInput()

    def process_formdata(self, valuelist):
        use_current_file = request.form.get(self.name + '-use-current-file')
        if use_current_file:
            file_path = app.config['UPLOADED_CUSTOM_DEST'] / use_current_file
            try:
                self.data = FileStorage(stream=file_path.open(),
                                        filename=use_current_file,
                                        name=self.name)
            except IOError:
                self.data = None
        else:
            super(FileField, self).process_formdata(valuelist)
