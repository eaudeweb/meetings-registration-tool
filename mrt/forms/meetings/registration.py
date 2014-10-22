from flask import g

from mrt.forms.base import BaseForm
from mrt.models import db
from mrt.models import Participant, Category

from wtforms import fields, widgets
from wtforms.validators import DataRequired


class RadioField(fields.SelectField):

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class RegistrationForm(BaseForm):

    def save(self):
        participant = Participant()
        participant.meeting_id = g.meeting.id

        for field_name, field in self._fields.items():
            cf = self._custom_fields[field.name]
            if cf.is_primary:
                value = field.data
                setattr(participant, field_name, value)
            else:
                cfv = cf.get_or_create_value(participant)
                cfv.value = field.data
                if not cfv.id:
                    db.session.add(cfv)

        if participant.id is None:
            db.session.add(participant)
        db.session.commit()

        return participant
