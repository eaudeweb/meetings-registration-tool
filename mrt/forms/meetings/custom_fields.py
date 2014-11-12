from uuid import uuid4

from flask import g
from flask.ext.uploads import UploadSet, IMAGES, TEXT, DOCUMENTS
from flask_wtf.file import FileField, FileAllowed
from flask.ext.babel import lazy_gettext as __

from sqlalchemy_utils import Choice

from werkzeug import FileStorage, OrderedMultiDict
from wtforms import fields
from wtforms.validators import DataRequired

from mrt.forms.base import BaseForm
from mrt.forms.base import BooleanField, CategoryField, CountryField
from mrt.models import CustomField, CustomFieldChoice
from mrt.models import Category
from mrt.models import db
from mrt.utils import unlink_participant_photo


custom_upload = UploadSet('custom', TEXT + DOCUMENTS + IMAGES)


_CUSTOM_FIELDS_MAP = {
    CustomField.TEXT: {'field': fields.StringField},
    CustomField.CHECKBOX: {'field': BooleanField},
    CustomField.IMAGE: {'field': FileField,
                        'validators': [FileAllowed(IMAGES)]},
    CustomField.SELECT: {'field': fields.SelectField},
    CustomField.COUNTRY: {'field': CountryField},
    CustomField.CATEGORY: {'field': CategoryField},
}


class _MagicForm(BaseForm):

    def save(self, participant):
        items = []
        for field_name, field in self._fields.items():
            cf = self._custom_fields[field.name]
            cfv = cf.get_or_create_value(participant)
            if isinstance(field.data, FileStorage):
                current_filename = cfv.value
                cfv.value = custom_upload.save(field.data,
                                               name=str(uuid4()) + '.')
                unlink_participant_photo(current_filename)
            else:
                cfv.value = field.data
            cfv.participant = participant
            if cf.is_primary:
                setattr(participant, cf.slug, cfv.value)
            if not cfv.id:
                db.session.add(cfv)
            items.append(cfv)
        db.session.commit()
        return items


def custom_form_factory(field_types=[], field_slugs=[],
                        registration_fields=False,
                        form=_MagicForm):
    fields = (CustomField.query.filter_by(meeting_id=g.meeting.id)
              .order_by(CustomField.sort))
    form_attrs = {
        '_custom_fields': OrderedMultiDict({c.slug: c for c in fields}),
    }

    if field_types:
        fields = fields.filter(CustomField.field_type.in_(field_types))

    if field_slugs:
        fields = fields.filter(CustomField.slug.in_(field_slugs))

    if registration_fields:
        fields = fields.filter_by(visible_on_registration_form=True)

    for f in fields:
        attrs = {'label': __(unicode(f.label)), 'validators': []}

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

        if f.field_type.code == CustomField.SELECT:
            query = CustomFieldChoice.query.filter_by(custom_field=f)
            attrs['choices'] = [(unicode(c.value), c.value) for c in query]
            if not f.required:
                attrs['choices'] = [('', '---')] + attrs['choices']
            attrs['coerce'] = unicode

        if f.field_type.code == CustomField.CATEGORY:
            query = (Category.query.filter_by(meeting=g.meeting)
                     .filter_by(category_type=Category.PARTICIPANT)
                     .order_by(Category.group, Category.sort))
            if registration_fields:
                query = query.filter_by(visible_on_registration_form=True)
            attrs['choices'] = [(c.id, c) for c in query]
            attrs['coerce'] = int

        # set field to form
        form_attrs[f.slug] = data['field'](**attrs)

    return type(form)(form.__name__, (form,), form_attrs)


def custom_object_factory(participant, field_type=[], obj=object):
    object_attrs = {}

    if participant:
        query = CustomField.query

        if participant.meeting:
            query = query.filter_by(meeting=participant.meeting)
        else:
            query = query.filter_by(meeting=g.meeting)

        if field_type:
            query = query.filter(CustomField.field_type.in_(field_type))

        for cf in query:
            if cf.is_primary:
                value = getattr(participant, cf.slug, None)
                if isinstance(value, Choice):
                    value = value.value
                object_attrs[cf.slug] = value
            else:
                cfv = (cf.custom_field_values
                       .filter_by(participant=participant)
                       .first())
                object_attrs[cf.slug] = cfv.value if cfv else None

    return type(obj)(obj.__name__, (obj,), object_attrs)
