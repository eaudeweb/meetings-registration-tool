from StringIO import StringIO
from flask import url_for
from py.path import local
from PIL import Image

from mrt.models import CustomFieldValue
from .factories import CustomFieldFactory, ParticipantFactory
from .factories import ProfilePictureFactory


def test_participant_picture_add(app):
    participant = ParticipantFactory()
    field = CustomFieldFactory(meeting=participant.meeting)
    data = {'picture': (StringIO('Test'), 'test.png')}
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])

    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.custom_field_upload',
                                   meeting_id=field.meeting.id,
                                   participant_id=participant.id,
                                   custom_field_slug='picture'), data=data)
        assert resp.status_code == 200
        picture = CustomFieldValue.query.filter_by(custom_field=field).first()
        assert picture is not None
        assert upload_dir.join(picture.value).check()


def test_participant_picture_edit(app):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    filename = pic.value
    upload_dir.ensure(pic.value)

    data = {'picture': (StringIO('Test'), 'test_edit.png')}
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.custom_field_upload',
                                   meeting_id=pic.custom_field.meeting.id,
                                   participant_id=pic.participant.id,
                                   custom_field_slug='picture'), data=data)
        assert resp.status_code == 200
        assert CustomFieldValue.query.scalar()
        assert filename != pic.value


def test_participant_picture_remove(app):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    upload_dir.ensure(pic.value)

    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.custom_field_upload',
                                     meeting_id=pic.custom_field.meeting.id,
                                     participant_id=pic.participant.id,
                                     custom_field_slug='picture'))
        assert resp.status_code == 200
        assert not upload_dir.join(pic.value).check()


def test_participant_picture_rotate(app):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    filename = pic.value
    image = Image.new('RGB', (250, 250), 'red')
    image.save(str(upload_dir.join(filename)))

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.custom_field_rotate',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)

        resp = client.post(url)
        assert resp.status_code == 200
        assert filename != pic.value
        assert not upload_dir.join(filename).check()
        assert upload_dir.join(pic.value).check()
