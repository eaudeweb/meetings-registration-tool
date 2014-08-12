from flask import g

from mrt.forms.meetings import custom_object_factory, custom_form_factory
from .factories import ProfilePictureFactory, CustomFieldFactory


def test_custom_object_factory(app):
    pic = ProfilePictureFactory()
    badge_field = CustomFieldFactory(label__english='badge',
                                     meeting=pic.custom_field.meeting)
    badge = ProfilePictureFactory(participant=pic.participant,
                                  custom_field=badge_field)
    attrs = (pic.custom_field.label.english, badge.custom_field.label.english)
    Obj = custom_object_factory(pic.participant, field_type='image')
    for attr in attrs:
        assert attr in Obj.__dict__


def test_custom_form_factory(app):
    pic = ProfilePictureFactory()
    g.meeting = pic.participant.meeting
    Obj = custom_object_factory(pic.participant, field_type='image')
    Form = custom_form_factory(pic.participant,
                               slug=pic.custom_field.label.english)
    with app.test_request_context():
        form = Form(obj=Obj())
        assert pic.custom_field.label.english in form._fields
