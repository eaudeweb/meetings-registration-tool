from flask import g
from wtforms import fields
from wtforms.validators import DataRequired

from mrt.models import db
from mrt.models import CategoryDefault, Category
from mrt.models import Translation
from mrt.utils import copy_model_fields

from mrt.forms.base import BaseForm


class MeetingCategoryAddForm(BaseForm):

    categories = fields.SelectMultipleField(validators=[DataRequired()],
                                            coerce=int)

    def __init__(self, *args, **kwargs):
        super(MeetingCategoryAddForm, self).__init__(*args, **kwargs)

        # exclude default categories that have the same name with
        # the categories for the current meeting
        subquery = (
            Category.query.join(Translation)
            .with_entities(Translation.english)
            .filter(Category.meeting == g.meeting)
            .subquery()
        )
        query = (
            CategoryDefault.query
            .filter(
                CategoryDefault.name.has(
                    Translation.english.notin_(subquery)))
            .all()
        )
        self.categories.choices = [(c.id, c.name) for c in query]

    def save(self):
        categories_default = CategoryDefault.query.filter(
            CategoryDefault.id.in_(self.categories.data))
        for category_default in categories_default:
            category = copy_model_fields(
                Category, category_default,
                 exclude=('id', 'name_id',))
            translation = Translation(english=category_default.name.english)
            db.session.add(translation)
            db.session.flush()
            category.name = translation
            category.meeting = g.meeting
            db.session.add(category)
        db.session.commit()
