from flask import g
from wtforms import fields
from wtforms.validators import DataRequired, Optional, Email
from wtforms.widgets import TextArea

from mrt.models import Participant, Category
from mrt.forms.base import BaseForm


LANGUAGE_CHOICES = [
    (slug, 'All {0} Speakers'.format(name))
    for slug, name in Participant.LANGUAGE_CHOICES
]


class BaseEmailForm(BaseForm):

    subject = fields.StringField(validators=[DataRequired()])
    message = fields.StringField(validators=[DataRequired()],
                                 widget=TextArea())


class BulkEmailForm(BaseEmailForm):

    language = fields.SelectField(
        'To', validators=[DataRequired()], choices=LANGUAGE_CHOICES,
    )

    categories = fields.SelectMultipleField(validators=[Optional()],
                                            coerce=int, choices=[])

    def __init__(self, *args, **kwargs):
        super(BulkEmailForm, self).__init__(*args, **kwargs)

        query = Category.query.filter(Category.meeting == g.meeting)
        self.categories.choices = [(c.id, c.title) for c in query]


class AcknowledgeEmailForm(BaseEmailForm):

    to = fields.StringField(validators=[DataRequired(), Email()])
