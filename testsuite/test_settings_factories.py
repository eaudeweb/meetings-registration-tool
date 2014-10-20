from flask import g

from mrt.forms.meetings import custom_object_factory, custom_form_factory
from mrt.models import CustomField
from .factories import ProfilePictureFactory, CustomFieldFactory


def test_custom_object_factory(app):
    pic = ProfilePictureFactory()
    g.meeting = pic.custom_field.meeting
    badge_field = CustomFieldFactory(label__english='badge',
                                     meeting=g.meeting)
    badge = ProfilePictureFactory(participant=pic.participant,
                                  custom_field=badge_field)
    attrs = (pic.custom_field.label.english,
             badge.custom_field.label.english)
    field_types = [CustomField.IMAGE]
    Obj = custom_object_factory(pic.participant, field_types)

    for attr in attrs:
        assert attr in Obj.__dict__


def test_custom_form_factory(app):
    pic = ProfilePictureFactory()
    g.meeting = pic.participant.meeting
    field_types = [CustomField.IMAGE]
    Obj = custom_object_factory(pic.participant, field_types)
    Form = custom_form_factory(field_slugs=[pic.custom_field.label.english])
    with app.test_request_context():
        form = Form(obj=Obj())
        assert pic.custom_field.label.english in form._fields
