from wtforms import fields, widgets
from mrt.models import db
from mrt.forms.meetings import ParticipantEditForm


class RadioField(fields.SelectField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class RegistrationForm(ParticipantEditForm):

    pass
