from collections import OrderedDict

from flask import request, g, current_app as app
from werkzeug import MultiDict

from wtforms import ValidationError, validators
from wtforms.widgets import TextInput, TextArea
from wtforms_alchemy import ClassMap
from wtforms_alchemy import ModelForm

from mrt.custom_country import CountryType
from mrt.forms.fields import CustomCountryField
from mrt.models import db
from mrt.models import Translation, Category, CategoryDefault, CustomField
from mrt.utils import slugify


class BaseForm(ModelForm):

    class Meta:
        type_map = ClassMap({CountryType: CustomCountryField})

    @classmethod
    def get_session(cls):
        return db.session

    def __init__(self, formdata=None, obj=None, **kwargs):
        formdata = formdata.copy() if formdata else MultiDict()
        if request.form and not len(formdata):
            formdata.update(request.form)
        if request.files:
            formdata.update(request.files)
        super(BaseForm, self).__init__(formdata=formdata, obj=obj, **kwargs)
        self.obj = obj


class TranslationBase(BaseForm):

    @property
    def translations(self):
        return [getattr(self, lang) for lang in app.config['TRANSLATIONS']]


class TranslationInputForm(TranslationBase):

    class Meta:
        model = Translation
        field_args = {
            'english': {
                'widget': TextInput()
            },
            'french': {
                'widget': TextInput()
            },
            'spanish': {
                'widget': TextInput()
            }
        }


class DefaultCategoryTitleInputForm(TranslationInputForm):

    duplicate_message = 'A category with this title exists'

    def validate_english(self, field):
        category = CategoryDefault.query.filter(
            CategoryDefault.title.has(english=field.data)).first()
        if category and self.obj != category.title:
            raise ValidationError(self.duplicate_message)


class CategoryTitleInputForm(TranslationInputForm):

    duplicate_message = 'A category with this title exists'

    def validate_english(self, field):
        category = Category.query.filter(
            Category.meeting == g.meeting,
            Category.title.has(english=field.data)).first()

        if category and self.obj != category.title:
            raise ValidationError(self.duplicate_message)


class CustomFieldLabelInputForm(TranslationInputForm):

    duplicate_message = 'A field with this label already exists'

    def validate_english(self, field):
        slug = slugify(field.data)
        custom_field = CustomField.query.filter(
            CustomField.slug == slug,
            CustomField.meeting == g.meeting,
            CustomField.custom_field_type == self.custom_field_type).first()

        if custom_field and self.obj != custom_field.label:
            raise ValidationError(self.duplicate_message)


class AdminCustomFieldLabelInputForm(TranslationInputForm):

    duplicate_message = 'A field with this label already exists'

    def validate_english(self, field):
        custom_field = CustomField.query.filter(
            CustomField.slug == slugify(field.data),
            CustomField.meeting == None,
            CustomField.custom_field_type == self.custom_field_type).first()

        if custom_field and self.obj != custom_field.label:
            raise ValidationError(self.duplicate_message)


def _check_if_required(form, field):
    french_field = form._fields.get('french')
    spanish_field = form._fields.get('spanish')

    if french_field and spanish_field:
        if bool(french_field.data) or bool(spanish_field.data):
            return validators.DataRequired()(form, field)

class DescriptionInputForm(TranslationBase):

    class Meta:
        model = Translation
        field_args = {
            'english': {
                'widget': TextArea(),
                'validators': [ _check_if_required]
            },
            'french': {
                'widget': TextArea()
            },
            'spanish': {
                'widget': TextArea()
            }
        }


class OrderedFieldsForm(BaseForm):

    def __iter__(self):
        field_order = getattr(self.Meta, 'field_order', None)
        if field_order and set(field_order) == set(self._fields.keys()):
            temp_fields = [(k, self._fields[k]) for k in field_order]
            self._fields = OrderedDict(temp_fields)
        return super(OrderedFieldsForm, self).__iter__()
