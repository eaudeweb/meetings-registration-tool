from flask import g

from mrt.forms.base import BaseForm
from mrt.models import Participant, Category

from wtforms import fields, widgets
from wtforms.validators import DataRequired


class RadioField(fields.SelectField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class RegistrationForm(BaseForm):

    def save(self):
        pass
