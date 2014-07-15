from wtforms_alchemy import ModelForm
from wtforms_alchemy import ModelFormField

from mrt.models import Staff
from mrt.forms.auth import UserForm


class StaffForm(ModelForm):

    class Meta:
        model = Staff

    user = ModelFormField(UserForm, label='User')
