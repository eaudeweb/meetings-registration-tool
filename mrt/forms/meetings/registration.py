from mrt.forms.meetings import ParticipantEditForm
from wtforms import fields, widgets


class RadioField(fields.SelectField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class RegistrationForm(ParticipantEditForm):

    pass
