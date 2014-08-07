from flask import g
from wtforms import fields
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import TextArea

from mrt.models import Participant, Category
from mrt.forms.base import BaseForm


LANGUAGE_CHOICES = [
    (slug, 'All {0} Speakers'.format(name))
    for slug, name in Participant.LANGUAGE_CHOICES
]


class BulkEmailForm(BaseForm):
    language = fields.SelectField(
        'To', validators=[DataRequired()], choices=LANGUAGE_CHOICES,
    )

    categories = fields.SelectMultipleField(validators=[Optional()],
                                            coerce=int, choices=[])
    subject = fields.StringField(validators=[DataRequired()])
    message = fields.StringField(validators=[DataRequired()],
                                 widget=TextArea())

    def __init__(self, *args, **kwargs):
        super(BulkEmailForm, self).__init__(*args, **kwargs)

        query = Category.query.filter(Category.meeting == g.meeting)
        self.categories.choices = [(c.id, c.title) for c in query]
