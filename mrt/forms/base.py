from wtforms_alchemy import ModelForm


class BaseForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
