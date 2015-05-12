from flask import g
from flask import current_app as app
from flask.ext.babel import lazy_gettext as __
from flask.ext.uploads import IMAGES
from flask_wtf.file import FileAllowed

from sqlalchemy_utils import Choice

from werkzeug import OrderedMultiDict
from wtforms.validators import DataRequired, Length, Optional

from mrt.forms.fields import CustomBooleanField, CustomCountryField
from mrt.forms.fields import CustomSelectField, CustomTextAreaField
from mrt.forms.fields import CustomStringField, CategoryField
from mrt.forms.fields import CustomImageField, CustomMultiCheckboxField
from mrt.forms.fields import CustomDocumentField, CustomDateField
from mrt.forms.fields import LanguageField, CustomRadioField
from mrt.forms.fields import EmailField, EmailRequired
from mrt.forms.fields import DOCUMENTS

from mrt.models import CustomField, CustomFieldChoice, Rule
from mrt.models import Category, Participant

from mrt.utils import CustomFieldLabel


_CUSTOM_FIELDS_MAP = {
    CustomField.TEXT: {'field': CustomStringField},
    CustomField.TEXT_AREA: {'field': CustomTextAreaField},
    CustomField.CHECKBOX: {'field': CustomBooleanField},
    CustomField.IMAGE: {'field': CustomImageField,
                        'validators': [FileAllowed(IMAGES)]},
    CustomField.DOCUMENT: {'field': CustomDocumentField,
                           'validators': [FileAllowed(DOCUMENTS)]},
    CustomField.SELECT: {'field': CustomSelectField},
    CustomField.LANGUAGE: {'field': LanguageField},
    CustomField.RADIO: {'field': CustomRadioField},
    CustomField.COUNTRY: {'field': CustomCountryField},
    CustomField.CATEGORY: {'field': CategoryField},
    CustomField.EMAIL: {'field': EmailField, 'validators': [EmailRequired()]},
    CustomField.EVENT: {'field': CustomBooleanField},
    CustomField.MULTI_CHECKBOX: {'field': CustomMultiCheckboxField},
    CustomField.DATE: {'field': CustomDateField, 'validators': [Optional()]},
}


def custom_form_factory(form, field_types=[], field_slugs=[],
                        excluded_field_types=[],
                        registration_fields=False):
    fields = (CustomField.query.filter_by(meeting_id=g.meeting.id)
              .order_by(CustomField.sort))
    form_attrs = {
        '_custom_fields': OrderedMultiDict({c.slug: c for c in fields}),
    }

    if field_types:
        fields = fields.filter(CustomField.field_type.in_(field_types))

    if field_slugs:
        fields = fields.filter(CustomField.slug.in_(field_slugs))

    if excluded_field_types:
        fields = fields.filter(
            ~CustomField.field_type.in_(excluded_field_types))

    if registration_fields:
        fields = fields.for_registration()

    if getattr(form, 'CUSTOM_FIELDS_TYPE', None):
        fields = fields.filter_by(custom_field_type=form.CUSTOM_FIELDS_TYPE)

    for f in fields:
        attrs = {'label': unicode(CustomFieldLabel(f.label)),
                 'validators': [],
                 'description': f.hint}

        data = _CUSTOM_FIELDS_MAP[f.field_type.code]

        # overwrite data if _CUSTOM_FIELDS_MAP attribute is present on form
        form_fields_map = getattr(form, '_CUSTOM_FIELDS_MAP', None)
        if form_fields_map:
            try:
                data = form_fields_map[f.field_type.code]
            except KeyError:
                pass

        if f.required:
            attrs['validators'].append(DataRequired())
        attrs['validators'].extend(data.get('validators', []))

        if f.max_length:
            attrs['validators'].append(Length(max=f.max_length))

        if f.field_type.code == CustomField.SELECT:
            query = CustomFieldChoice.query.filter_by(custom_field=f)
            attrs['choices'] = [(unicode(c.value), __(c.value.english))
                                for c in query]
            if not f.required:
                attrs['choices'] = [('', '---')] + attrs['choices']
            attrs['coerce'] = unicode

        if f.field_type.code == CustomField.LANGUAGE:
            attrs['choices'] = [i for i in Participant.LANGUAGE_CHOICES
                                if i[0].lower() in app.config['TRANSLATIONS']]
            if not f.required:
                attrs['choices'] = [('', '---')] + attrs['choices']

            attrs['coerce'] = unicode

        if f.field_type.code == CustomField.CATEGORY:
            query = Category.get_categories_for_meeting(
                form.CUSTOM_FIELDS_TYPE)
            if registration_fields:
                query = query.filter_by(visible_on_registration_form=True)
            attrs['choices'] = [(c.id, c) for c in query]
            attrs['coerce'] = int

        if f.field_type.code in (CustomField.MULTI_CHECKBOX,CustomField.RADIO):
            query = CustomFieldChoice.query.filter_by(custom_field=f)
            attrs['choices'] = [(unicode(c.value), c.value) for c in query]
            attrs['coerce'] = unicode

        # set field to form
        # _set_rules_for_custom_fields(f, attrs)
        field = data['field'](**attrs)
        setattr(field, 'field_type', f.field_type.code)
        form_attrs[f.slug] = field

    form_attrs['rules'] = Rule.get_rules_for_fields(fields)
    return type(form)(form.__name__, (form,), form_attrs)


def custom_object_factory(participant, field_type=[], obj=object):
    object_attrs = {}

    if participant:
        object_attrs['_participant'] = participant
        if participant.participant_type in (CustomField.PARTICIPANT,
                                            CustomField.MEDIA):
            custom_field_type = participant.participant_type
        else:
            if participant.participant_type == participant.DEFAULT:
                custom_field_type = CustomField.PARTICIPANT
            else:
                custom_field_type = CustomField.MEDIA

        query = (CustomField.query
                 .filter_by(meeting=participant.meeting or g.meeting)
                 .filter_by(custom_field_type=custom_field_type))
        if field_type:
            query = query.filter(CustomField.field_type.in_(field_type))

        for cf in query:
            if cf.is_primary:
                value = getattr(participant, cf.slug, None)
                if isinstance(value, Choice):
                    value = value.value
                object_attrs[cf.slug] = value
            else:
                data = _CUSTOM_FIELDS_MAP[cf.field_type.code]
                field = data['field']
                object_attrs[cf.slug] = field.provide_data(cf, participant)
    return type(obj)(obj.__name__, (obj,), object_attrs)
