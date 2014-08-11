import json
from StringIO import StringIO
from flask import url_for
from pyquery import PyQuery
from py.path import local

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

        html = PyQuery(json.loads(resp.data)['html'])('a')
        filename = html.attr('href').split('/')[-1]
        assert upload_dir.join(filename).check()


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
