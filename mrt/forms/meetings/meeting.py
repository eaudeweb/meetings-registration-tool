from flask.ext.login import current_user
from flask_wtf.file import FileField, FileAllowed
from wtforms import fields, widgets, Form
from wtforms.validators import ValidationError, InputRequired, Length
from wtforms_alchemy import ModelFormField
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from mrt.models import db, Meeting, Staff, Participant
from mrt.models import Phrase, PhraseDefault, Translation
from mrt.models import CustomField, CustomFieldChoice
from mrt.models import MeetingType, Category, Condition, ConditionValue

from mrt.forms.base import BaseForm, TranslationInputForm, OrderedFieldsForm
from mrt.forms.fields import MeetingSettingsField
from mrt.forms.fields import CategoryField, EmailRequired, EmailField
from mrt.forms.fields import LanguageField

from mrt.utils import copy_attributes, Logo, logos_upload
from mrt.definitions import MEETING_SETTINGS


_CUSTOM_FIELD_MAPPER = {
    'StringField': CustomField.TEXT,
    'BooleanField': CustomField.CHECKBOX,
    'SelectField': CustomField.SELECT,
    'RadioField': CustomField.RADIO,
    'CountryField': CustomField.COUNTRY,
    'CategoryField': CustomField.CATEGORY,
    'LanguageField': CustomField.LANGUAGE,
    'EmailField': CustomField.EMAIL,
    'DateField': CustomField.DATE,
    'TextAreaField': CustomField.TEXT_AREA,
}


class MeetingEditForm(BaseForm):

    class Meta:
        model = Meeting
        field_args = {
            'venue_address': {
                'widget': widgets.TextArea()
            },
            'date_start': {
                'format': '%d.%m.%Y',
            },
            'date_end': {
                'format': '%d.%m.%Y',
            }
        }

    title = ModelFormField(TranslationInputForm, label='Description')
    badge_header = ModelFormField(TranslationInputForm, label='Badge header')
    venue_city = ModelFormField(TranslationInputForm, label='City')
    meeting_type_slug = fields.SelectField('Meeting Type')
    photo_field_id = fields.SelectField('Photo Field', coerce=int)
    address_field_id = fields.SelectField('Address Field', coerce=int)
    telephone_field_id = fields.SelectField('Telephone Field', coerce=int)
    media_photo_field_id = fields.SelectField('Media Photo Field', coerce=int)
    settings = MeetingSettingsField('Settings', choices=MEETING_SETTINGS)

    def __init__(self, *args, **kwargs):
        super(MeetingEditForm, self).__init__(*args, **kwargs)
        self.badge_header.english.validators = []
        delattr(self.badge_header.english.flags, 'required')
        self.meeting_type_slug.choices = [
            (mt.slug, mt.label) for mt in MeetingType.query.ignore_def()]
        self.photo_field_id.choices = [(0, '-----')]
        self.address_field_id.choices = [(0, '-----')]
        self.telephone_field_id.choices = [(0, '-----')]
        self.media_photo_field_id.choices = [(0, '-----')]
        if self.obj:
            image_query = self.obj.custom_fields.filter_by(
                field_type=CustomField.IMAGE)
            participant_query = image_query.filter_by(
                custom_field_type=CustomField.PARTICIPANT)
            image_fields = [(x.id, x.label) for x in participant_query]
            self.photo_field_id.choices += image_fields
            media_query = image_query.filter_by(
                custom_field_type=CustomField.MEDIA)
            image_fields = [(x.id, x.label) for x in media_query]
            self.media_photo_field_id.choices += image_fields

            text_query = (self.obj.custom_fields
                .filter_by(is_primary=False, is_protected=False)
                .filter(
                    CustomField.field_type.in_([CustomField.TEXT, CustomField.TEXT_AREA])
                )
            )
            text_fields = [(x.id, x.label) for x in text_query]
            self.address_field_id.choices += text_fields
            self.telephone_field_id.choices += text_fields

    def validate_settings(self, field):
        settings = dict(MEETING_SETTINGS)
        for key in field.data:
            if key not in settings:
                raise ValidationError("Setting doesn't exist")

    def _clean_badge_header(self, meeting):
        if not self.badge_header.data['english']:
            old_badge_header, meeting.badge_header = meeting.badge_header, None
            if old_badge_header.id:
                db.session.delete(old_badge_header)

    def _save_phrases(self, meeting):
        phrases_default = (
            PhraseDefault.query
            .filter_by(meeting_type_slug=meeting.meeting_type_slug)
        )
        for phrase_default in phrases_default:
            phrase = copy_attributes(Phrase(), phrase_default)
            phrase.description = (
                copy_attributes(Translation(), phrase_default.description)
                if phrase_default.description else Translation(english=''))
            phrase.meeting = meeting
            db.session.add(phrase)
            db.session.flush()

    def _save_categories(self, meeting):
        for category_default in meeting.meeting_type.default_categories:
            category = copy_attributes(Category(), category_default)
            category.title = copy_attributes(Translation(),
                                             category_default.title)
            category.tags = category_default.tags
            category.meeting = meeting
            db.session.add(category)
            db.session.flush()

    def _save_custom_field(self, meeting):
        add_custom_fields_for_meeting(meeting, form_class=ParticipantDummyForm)
        query = (
            CustomField.query.filter_by(meeting=meeting)
            .with_entities(CustomField.sort)
            .order_by(desc(CustomField.sort))
            .first())
        last_sort = query[0] + 1

        # Copy default custom fields for meeting type
        for field_default in meeting.meeting_type.default_fields:
            field = copy_attributes(CustomField(), field_default)
            field.label = copy_attributes(Translation(), field_default.label)
            field.sort = last_sort
            last_sort += 1
            field.meeting = meeting
            db.session.add(field)
        db.session.flush()

    def save(self):
        meeting = self.obj or Meeting()
        # Store meetings settings to prevent overwriting them
        initial_settings = {k: v for k, v in (meeting.settings or {}).items()
                            if k not in dict(MEETING_SETTINGS)}
        self.populate_obj(meeting)
        meeting.settings.update(initial_settings)
        meeting.photo_field_id = meeting.photo_field_id or None
        meeting.address_field_id = meeting.address_field_id or None
        meeting.telephone_field_id = meeting.telephone_field_id or None
        meeting.media_photo_field_id = meeting.media_photo_field_id or None
        self._clean_badge_header(meeting)
        if meeting.id is None:
            meeting.owner = current_user.staff
            db.session.add(meeting)
            self._save_phrases(meeting)
            self._save_categories(meeting)
            self._save_custom_field(meeting)
        if meeting.media_participant_enabled:
            add_custom_fields_for_meeting(
                meeting, form_class=MediaParticipantDummyForm)
        db.session.commit()
        return meeting


class MeetingCloneForm(MeetingEditForm):
    def __init__(self, *args, **kwargs):
        super(MeetingCloneForm, self).__init__(*args, **kwargs)
        if not self.acronym.raw_data and self.acronym.data == self.obj.acronym:
            self.acronym.data = None

    def validate_acronym(self, field):
        try:
            Meeting.query.filter_by(acronym=field.data).one()
            raise ValidationError('Acronym exists')
        except NoResultFound:
            pass

    def _clone_relation(self, meeting, children, translation_attrs=[],
                        exclude_fk=True):
        for child in children:
            clone = copy_attributes(child.__class__(), child,
                                    exclude_fk=exclude_fk)
            for attr in translation_attrs:
                setattr(clone, attr,
                        copy_attributes(Translation(), getattr(child, attr)))
            clone.meeting = meeting
            db.session.add(clone)
            db.session.flush()

    def _clone_custom_fields(self, meeting, custom_fields,
                             translation_attrs=[]):
        for custom_field in custom_fields:
            clone = copy_attributes(custom_field.__class__(), custom_field)
            for attr in translation_attrs:
                setattr(clone, attr, copy_attributes(Translation(),
                        getattr(custom_field, attr)))
            clone.meeting = meeting
            db.session.add(clone)

            for choice in custom_field.choices:
                choice_clone = CustomFieldChoice(custom_field=clone)
                setattr(choice_clone, 'value', copy_attributes(Translation(),
                        getattr(choice, 'value')))
                db.session.add(choice_clone)

            db.session.flush()

    def _clone_categories(self, meeting, categories):
        for category in categories:
            clone = copy_attributes(Category(), category)
            clone.tags = category.tags
            clone.title = copy_attributes(Translation(), category.title)
            clone.meeting = meeting
            db.session.add(clone)
            db.session.flush()

    def _clone_rules(self, meeting, rules):
        for rule in rules:
            rule_clone = copy_attributes(rule.__class__(), rule,
                                         exclude_fk=True)
            rule_clone.meeting = meeting
            db.session.add(rule_clone)

            for condition in rule.conditions.all():
                condition_clone = Condition()
                condition_type = condition.field.custom_field_type
                condition_label = condition.field.label.english
                field = meeting.custom_fields.filter(
                    CustomField.label.has(english=condition_label),
                    CustomField.custom_field_type == condition_type).one()
                condition_clone.field = field
                condition_clone.rule = rule_clone
                db.session.add(condition_clone)

                for condition_value in condition.values.all():
                    condition_value_clone = ConditionValue()
                    condition_value_clone.condition = condition_clone
                    value = condition_value.value
                    if condition.field.field_type == CustomField.CATEGORY:
                        title = Category.query.get(int(value)).title.english
                        value = meeting.categories.filter(
                            Category.title.has(english=title)).scalar().id
                    condition_value_clone.value = value
                    db.session.add(condition_value_clone)

            for action in rule.actions.all():
                action_clone = copy_attributes(action.__class__(), action,
                                               exclude_fk=True)
                action_clone.rule = rule_clone
                field = meeting.custom_fields.filter_by(
                    slug=action.field.slug).one()
                action_clone.field = field
                db.session.add(action_clone)

            db.session.flush()

    def save(self):
        meeting = Meeting()
        self.populate_obj(meeting)
        meeting.photo_field_id = meeting.photo_field_id or None
        meeting.media_photo_field_id = meeting.media_photo_field_id or None
        self._clone_custom_fields(meeting, self.obj.custom_fields, ('label', ))
        self._clone_categories(meeting, self.obj.categories)
        self._clone_relation(meeting, self.obj.phrases, ('description', ))
        self._clone_relation(meeting, self.obj.role_users, exclude_fk=False)
        self._clone_relation(meeting, self.obj.user_notifications,
                             exclude_fk=False)
        self._clone_rules(meeting, self.obj.rules)
        meeting.owner = self.obj.owner
        if self.obj.photo_field_id:
            meeting.photo_field = (meeting.custom_fields
                                   .filter_by(slug=meeting.photo_field.slug)
                                   .first())
        if self.obj.media_photo_field_id:
            meeting.media_photo_field = (
                meeting.custom_fields
                .filter_by(slug=meeting.media_photo_field.slug)
                .first())
        db.session.add(meeting)
        db.session.commit()
        return meeting


class ParticipantDummyForm(OrderedFieldsForm):

    CUSTOM_FIELD_TYPE = 'participant'

    category_id = CategoryField('Category', validators=[InputRequired()],
                                coerce=int, choices=[])
    email = EmailField('Email', validators=[EmailRequired(), InputRequired()])

    language = LanguageField('Working language',
                             choices=Participant.LANGUAGE_CHOICES)

    class Meta:
        model = Participant
        exclude = ('deleted', 'registration_token', 'participant_type')
        field_order = ('title', 'first_name', 'last_name', 'badge_name',
                       'language', 'country', 'email', 'category_id',
                       'represented_organization', 'represented_country',
                       'represented_region', 'attended', 'verified',
                       'credentials')
        visible_on_registration_form = (
            'title', 'first_name', 'last_name', 'email', 'category_id',
            'language', 'country', 'represented_country',
            'represented_organization',)
        field_args = {
            'language': {'validators': [InputRequired()]},
            'country': {'validators': [InputRequired()]}
        }
        protected_fields = ('title', 'email', 'category_id', 'country')


class DefaultParticipantDummyForm(BaseForm):

    CUSTOM_FIELD_TYPE = 'participant'

    email = EmailField('Email', validators=[EmailRequired(), InputRequired()])

    class Meta:
        model = Participant
        exclude = ('deleted', 'registration_token', 'participant_type',
                   'attended', 'verified', 'credentials')
        visible_on_registration_form = []
        field_args = {
            'language': {'validators': [InputRequired()]},
            'country': {'validators': [InputRequired()]}
        }
        protected_fields = []


class MediaParticipantDummyForm(OrderedFieldsForm):

    CUSTOM_FIELD_TYPE = 'media'

    category_id = CategoryField('Category', validators=[InputRequired()],
                                coerce=int, choices=[])
    email = EmailField('Email', validators=[EmailRequired(), InputRequired()])

    class Meta:
        model = Participant
        only = ('title', 'first_name', 'last_name', 'email', 'category_id')
        visible_on_registration_form = (
            'title', 'first_name', 'last_name', 'email', 'category_id')
        field_order = ('title', 'first_name', 'last_name', 'email',
                       'category_id')
        protected_fields = ('title', 'email', 'category_id', 'country')


class DefaultMediaParticipantDummyForm(BaseForm):

    CUSTOM_FIELD_TYPE = 'media'

    email = EmailField('Email', validators=[EmailRequired(), InputRequired()])

    class Meta:
        model = Participant
        only = ('title', 'first_name', 'last_name', 'email')
        visible_on_registration_form = []
        protected_fields = []


class MeetingFilterForm(BaseForm):

    meeting_type = fields.SelectField('Filter by type', choices=[])

    def __init__(self, *args, **kwargs):
        super(MeetingFilterForm, self).__init__(*args, **kwargs)
        choices = [(m.slug, m.label) for m in MeetingType.query.ignore_def()]
        self.meeting_type.choices = [('', 'All')] + choices


class MeetingChangeOwnerForm(BaseForm):

    owner_id = fields.SelectField('Owner', coerce=int)

    def __init__(self, *args, **kwargs):
        super(MeetingChangeOwnerForm, self).__init__(*args, **kwargs)
        self.owner_id.choices = [(i.id, i) for i in Staff.query.all()]

    def save(self):
        self.populate_obj(self.obj)
        db.session.commit()


class MeetingLogoEditForm(Form):

    logo = FileField('Image',
                     [FileAllowed(logos_upload, 'Image is not valid')])

    def save(self, logo_slug):
        if self.logo.data:
            logo = Logo(logo_slug)
            logo.save(self.logo.data)
            return logo


def _extract_max_length_from_field(field):
    try:
        [length_validator] = [i for i in field.validators
                              if isinstance(i, Length)]
        return length_validator.max
    except ValueError:
        pass


def add_custom_fields_for_meeting(meeting, form_class=ParticipantDummyForm):
    """Adds participants fields as CustomFields to meeting."""
    form = form_class()
    for i, field in enumerate(form):
        query = (
            CustomField.query
            .filter_by(slug=field.name, meeting=meeting)
            .filter_by(custom_field_type=form.CUSTOM_FIELD_TYPE)
        )
        if query.scalar():
            continue
        custom_field = CustomField()
        custom_field.meeting = meeting
        custom_field.slug = field.name
        custom_field.label = Translation(english=unicode(field.label.text))
        custom_field.required = field.flags.required
        custom_field.field_type = _CUSTOM_FIELD_MAPPER[field.type]
        custom_field.is_primary = True
        custom_field.custom_field_type = form.CUSTOM_FIELD_TYPE
        custom_field.max_length = _extract_max_length_from_field(field)

        if field.name in form.meta.visible_on_registration_form:
            custom_field.visible_on_registration_form = True
        else:
            custom_field.visible_on_registration_form = False

        if field.name in form.meta.protected_fields:
            custom_field.is_protected = True
        else:
            custom_field.is_protected = False

        custom_field.sort = i + 1
        db.session.add(custom_field)

        if custom_field.field_type in (CustomField.SELECT,
                                       CustomField.LANGUAGE):
            _add_choice_values_for_custom_field(custom_field, field.choices)

    db.session.commit()


def _add_choice_values_for_custom_field(custom_field, choices):
    """Adds CustomFieldChoices for CustomField."""
    for value, label in (choices or []):
        custom_field_choice = CustomFieldChoice(custom_field=custom_field)
        custom_field_choice.value = Translation(english=value)
        db.session.add(custom_field_choice)
