from itertools import groupby
from uuid import uuid4

from flask import current_app as app
from flask import render_template, request
from flask.ext.uploads import UploadSet, IMAGES
from flask_wtf.file import FileField as _FileField


from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import Country
from werkzeug import FileStorage

from wtforms import widgets, fields, validators
from wtforms.widgets.core import html_params, HTMLString
from wtforms_alchemy import CountryField as _CountryField

from mrt.models import MeetingType
from mrt.utils import validate_email, unlink_participant_photo


custom_upload = UploadSet('custom', IMAGES)


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
                    subfield(),
                    label)
                )
            html.append('<li class="group-%s"></li>' % group)
            html.append('<li class="separator"></li>')

        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class FileInputWidget(object):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        return HTMLString(render_template(
            'meetings/registration/_image_widget.html',
            field=field))


class EmailRequired(object):
    """Participant email validator. Multiple emails are allowed, separated by
    comma, but have to be well formated."""

    def __init__(self):
        self.message = 'Invalid email address'
        self.split_char = ','

    def __call__(self, form, field):
        emails = field.data.split(self.split_char)
        for email in emails:
            if not validate_email(email.strip()):
                raise validators.ValidationError(self.message)


class SlugUnique(object):

    def __call__(self, form, field):
        if form.obj:
            if form.obj.slug == field.data:
                return True
            else:
                raise validators.ValidationError(
                    'Meeting type slug is not editable')
        try:
            MeetingType.query.filter_by(slug=field.data).one()
            raise validators.ValidationError(
                'Another meeting type with this slug exists')
        except NoResultFound:
            pass


class CustomBaseFieldMixin():

    def save(self, cf, participant):
        cfv = cf.get_or_create_value(participant)
        cfv.value = self.data
        return cfv


class BooleanField(fields.BooleanField):

    def process_data(self, data):
        self.data = True if (data == 'true' or data is True) else False


class MultiCheckboxField(fields.SelectMultipleField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class MeetingSettingsField(MultiCheckboxField):

    def process_data(self, data):
        data = data or {}
        try:
            self.data = [setting for setting in data if data[setting]]
        except TypeError:
            raise TypeError('Parameter data must be a dict')

    def process_formdata(self, valuelist):
        self.data = {setting: True for setting in valuelist}


class CustomMultiCheckboxField(CustomBaseFieldMixin, MultiCheckboxField):
    pass


class CategoryField(CustomBaseFieldMixin, fields.RadioField):

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


class _BaseFileFieldMixin(object):

    def save(self, cf, participant):
        cfv = cf.get_or_create_value(participant)
        current_filename = cfv.value
        cfv.value = custom_upload.save(self.data, name=str(uuid4()) + '.')
        unlink_participant_photo(current_filename)
        return cfv


class RegistrationFileField(_BaseFileFieldMixin, _FileField):

    widget = FileInputWidget()

    def __init__(self, *args, **kwargs):
        super(RegistrationFileField, self).__init__(*args, **kwargs)
        self._use_current_file = False

    def process_formdata(self, valuelist):
        use_current_file = request.form.get(self.name + '-use-current-file')
        if use_current_file:
            self._use_current_file = True
            file_path = app.config['UPLOADED_CUSTOM_DEST'] / use_current_file
            try:
                self.data = FileStorage(stream=file_path.open(),
                                        filename=use_current_file,
                                        name=self.name)
            except IOError:
                self.data = None
        else:
            super(RegistrationFileField, self).process_formdata(valuelist)

    def process_data(self, value):
        super(RegistrationFileField, self).process_data(value)
        if isinstance(value, basestring):
            self._use_current_file = True
            file_path = app.config['UPLOADED_CUSTOM_DEST'] / value
            try:
                self.data = FileStorage(stream=file_path.open(),
                                        filename=file_path.basename(),
                                        name=self.name)
            except IOError:
                self.data = None


class CustomFileField(_BaseFileFieldMixin, _FileField):
    pass


class EmailField(CustomBaseFieldMixin, fields.StringField):

    validators = [EmailRequired()]


class CustomStringField(CustomBaseFieldMixin, fields.StringField):
    pass


class CustomBooleanField(CustomBaseFieldMixin, BooleanField):
    pass


class CustomSelectField(CustomBaseFieldMixin, fields.SelectField):

    def process_data(self, value):
        super(CustomSelectField, self).process_data(value)
        if self.data == 'None':
            self.data = ''


class CustomCountryField(CustomBaseFieldMixin, CountryField):

    def save(self, cf, participant):
        cfv = cf.get_or_create_value(participant)
        cfv.value = self.data.code
        return cfv


class CustomTextAreaField(CustomBaseFieldMixin, fields.TextAreaField):
    pass


class SelectMultipleFieldWithoutValidation(fields.SelectMultipleField):

    pre_validate = lambda self, form: None
