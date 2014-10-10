from uuid import uuid4

from flask import g
from flask.ext.uploads import UploadSet, IMAGES, TEXT, DOCUMENTS
from flask_wtf.file import FileField, FileAllowed

from werkzeug import FileStorage, OrderedMultiDict
from wtforms import fields
from wtforms.validators import DataRequired
from wtforms_alchemy import CountryField

from mrt.forms.base import BaseForm
from mrt.forms.base import BooleanField, CategoryField
from mrt.models import CustomField, CustomFieldValue, CustomFieldChoice
from mrt.models import Category
from mrt.models import db
from mrt.utils import unlink_participant_photo


custom_upload = UploadSet('custom', TEXT + DOCUMENTS + IMAGES)


class _MagicForm(BaseForm):

    MAP = {
        CustomField.TEXT: {'field': fields.StringField},
        CustomField.CHECKBOX: {'field': BooleanField},
        CustomField.IMAGE: {'field': FileField,
                            'validators': [FileAllowed(IMAGES)]},
        CustomField.SELECT: {'field': fields.SelectField},
        CustomField.COUNTRY: {'field': CountryField},
        CustomField.CATEGORY: {'field': CategoryField},
    }

    def save(self, participant=None):
        participant = self._participant or participant
        items = []
        for field_name, field in self._fields.items():
            custom_field_value = (
                CustomFieldValue.query
                .filter(CustomFieldValue.custom_field.has(slug=field_name))
                .filter(CustomFieldValue.participant == participant)
                .scalar())
            custom_field_value = custom_field_value or CustomFieldValue()
            if isinstance(field.data, FileStorage):
                current_filename = custom_field_value.value
                custom_field_value.value = custom_upload.save(
                    field.data, name=str(uuid4()) + '.')
                unlink_participant_photo(current_filename)
            else:
                custom_field_value.value = field.data
            custom_field_value.custom_field = self._custom_fields[field_name]
            custom_field_value.participant = participant
            if not custom_field_value.id:
                db.session.add(custom_field_value)
            items.append(custom_field_value)
        db.session.commit()
        return items


def custom_form_factory(participant, field_type=[], form=_MagicForm):
    fields = (CustomField.query.filter_by(meeting_id=g.meeting.id)
              .order_by(CustomField.sort))
    form_attrs = {
        '_custom_fields': OrderedMultiDict({c.slug: c for c in fields}),
        '_participant': participant,
    }

    if field_type:
        fields = fields.filter(CustomField.field_type.in_(field_type))

    for f in fields:
        attrs = {'label': f.label, 'validators': []}
        data = form.MAP[f.field_type.code]
        if f.required:
            attrs['validators'].append(DataRequired())
        attrs['validators'].extend(data.get('validators', []))

        if f.field_type.code == CustomField.SELECT:
            query = CustomFieldChoice.query.filter_by(custom_field=f)
            attrs['choices'] = [(c.id, c.value) for c in query]

        if f.field_type.code == CustomField.CATEGORY:
            query = (Category.query.filter_by(meeting=g.meeting)
                     .filter_by(category_type=Category.PARTICIPANT))
            attrs['choices'] = [(c.id, c.title) for c in query]

        # set field to form
        form_attrs[f.slug] = data['field'](**attrs)

    return type(form)(form.__name__, (form,), form_attrs)
