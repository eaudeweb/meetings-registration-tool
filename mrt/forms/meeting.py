from flask import current_app as app
from flask import g
from wtforms import fields, widgets
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelFormField

from mrt.models import db
from mrt.models import Meeting
from mrt.models import CategoryDefault, Category
from mrt.utils import copy_model_fields

from .base import BaseForm, TranslationInpuForm


class MeetingEditForm(BaseForm):

    class Meta:
        model = Meeting
        field_args = {
            'venue_address': {
                'widget': widgets.TextArea()
            },
            'date_start': {
                'format': '%d.%m.%Y'
            },
            'date_end': {
                'format': '%d.%m.%Y'
            }
        }

    title = ModelFormField(TranslationInpuForm, label='Description')
    venue_city = ModelFormField(TranslationInpuForm, label='City')
    meeting_type = fields.SelectField('Meeting Type')

    def __init__(self, *args, **kwargs):
        super(MeetingEditForm, self).__init__(*args, **kwargs)
        self.meeting_type.choices = app.config.get('MEETING_TYPES', [])

    def save(self):
        meeting = self.obj or Meeting()
        self.populate_obj(meeting)
        if meeting.id is None:
            db.session.add(meeting)
        db.session.commit()
        return meeting


class MeetingCategoryAddForm(BaseForm):

    categories = fields.SelectMultipleField(validators=[DataRequired()],
                                            coerce=int)

    def __init__(self, *args, **kwargs):
        super(MeetingCategoryAddForm, self).__init__(*args, **kwargs)
        self.categories.choices = [
            (c.id, c.name) for c in CategoryDefault.query.all()]

    def save(self):
        categories_default = CategoryDefault.query.filter(
            CategoryDefault.id.in_(self.categories.data))
        for category_default in categories_default:
            category = copy_model_fields(Category, category_default,
                                         exclude=('id', 'name_id'))
            category.name = category_default.name
            category.meeting = g.meeting
            db.session.add(category)
        db.session.commit()
