from flask import g
from wtforms import fields
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelFormField

from mrt.models import db
from mrt.models import CategoryDefault, Category
from mrt.models import RoleUser, Role, Staff, User
from mrt.models import CustomField
from mrt.models import Translation
from mrt.utils import copy_model_fields, duplicate_uploaded_file

from mrt.forms.base import BaseForm, TranslationInpuForm


class MeetingCategoryAddForm(BaseForm):

    categories = fields.SelectMultipleField(validators=[DataRequired()],
                                            coerce=int, choices=[])

    def __init__(self, *args, **kwargs):
        super(MeetingCategoryAddForm, self).__init__(*args, **kwargs)

        # exclude default categories that have the same name with
        # the categories for the current meeting
        subquery = (
            Category.query.join(Translation)
            .with_entities(Translation.english)
            .filter(Category.meeting == g.meeting)
            .subquery()
        )
        query = (
            CategoryDefault.query
            .filter(
                CategoryDefault.title.has(
                    Translation.english.notin_(subquery)))
            .all()
        )
        self.categories.choices = [(c.id, c.title) for c in query]

    def save(self):
        categories_default = CategoryDefault.query.filter(
            CategoryDefault.id.in_(self.categories.data))
        for category_default in categories_default:
            category = copy_model_fields(
                Category, category_default,
                exclude=('id', 'title_id', 'background'))
            translation = Translation(english=category_default.title.english)
            db.session.add(translation)
            db.session.flush()
            category.title = translation
            category.meeting = g.meeting
            filename = duplicate_uploaded_file(category_default.background,
                                               'backgrounds')
            if filename:
                category.background = filename.basename()
            db.session.add(category)
        db.session.commit()


class CustomFieldEditForm(BaseForm):

    label = ModelFormField(TranslationInpuForm, label='Field label')

    class Meta:
        model = CustomField

    def save(self):
        custom_field = self.obj or CustomField()
        self.populate_obj(custom_field)
        custom_field.meeting = g.meeting
        if not custom_field.slug:
            db.session.add(custom_field)
        db.session.commit()


class CustomFieldMagicForm(BaseForm):

    MAP = {
        'text': fields.StringField,
        'image': fields.FileField,
    }

    def save(self):
        pass


def custom_form_factory(field_type=None, form=CustomFieldMagicForm):
    custom_fields = CustomField.query.filter_by(meeting_id=g.meeting.id)
    if field_type:
        custom_fields = custom_fields.filter_by(field_type=field_type)

    form_attrs = {}
    for f in custom_fields:
        field_attrs = {'label': f.label, 'validators': []}
        if f.required:
            field_attrs['validators'].append(DataRequired())
        form_attrs[f.slug] = form.MAP[f.field_type.code](*field_attrs)

    return type(form)(form.__name__, (form,), form_attrs)


class RoleUserEditForm(BaseForm):

    class Meta:
        model = RoleUser

    user_id = fields.SelectField('User',
                                 validators=[DataRequired()],
                                 coerce=int)
    role_id = fields.SelectField('Role',
                                 validators=[DataRequired()],
                                 coerce=int)

    def __init__(self, *args, **kwargs):
        if kwargs['obj']:
            kwargs.setdefault('user_id', kwargs['obj'].user.id)
            kwargs.setdefault('role_id', kwargs['obj'].role.id)
        super(RoleUserEditForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(
            x.user.id, x.user.email) for x in Staff.query.all()]
        self.role_id.choices = [(x.id, x.name) for x in Role.query.all()]

    def save(self):
        user_role = self.obj or self.meta.model()
        user_role.user = User.query.get_or_404(self.user_id.data)
        user_role.role = Role.query.get_or_404(self.role_id.data)
        user_role.meeting = g.meeting
        if user_role.id is None:
            db.session.add(user_role)
        db.session.commit()
