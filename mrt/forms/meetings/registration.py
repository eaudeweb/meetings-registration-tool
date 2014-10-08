from flask import g

from mrt.forms.base import BaseForm
from mrt.models import Participant, Category

from wtforms import fields, widgets
from wtforms.validators import DataRequired


class RadioField(fields.SelectField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class RegistrationForm(BaseForm):

    category_id = fields.RadioField('Category', validators=[DataRequired()],
                                    coerce=int, choices=[])

    class Meta:
        model = Participant
        only = ('title', 'first_name', 'last_name', 'email',
                'country', 'language', 'represented_country',
                'represented_organization',)

        field_args = {}

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        query = (
            Category.query.filter_by(meeting_id=g.meeting.id)
            .filter_by(visible_on_registration_form=True))
        self.category_id.choices = [(c.id, c.title) for c in query]

    def save(self):
        pass
