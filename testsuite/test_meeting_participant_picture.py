import os
from StringIO import StringIO
from flask import url_for
from flask.ext.thumbnails import Thumbnail
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


def test_participant_picture_remove_thumbnail(app):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    thumb_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                      app.config['PATH_CUSTOM_KEY'])
    image = Image.new('RGB', (250, 250), 'red')
    image.save(str(upload_dir.join(pic.value)))

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.custom_field_rotate',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)

        resp = client.post(url)
        assert resp.status_code == 200
        thumb_name, thumb_fm = os.path.splitext(pic.value)
        thumb_full_name = Thumbnail._get_name(thumb_name, thumb_fm,
                                              '200x200', 85)
        assert thumb_dir.join(thumb_full_name).check()

        url = url_for('meetings.custom_field_upload',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert not thumb_dir.join(thumb_full_name).check()


def test_participant_picture_remove_crop(app, user):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    crop_dir = local(app.config['UPLOADED_CROP_DEST'] /
                     app.config['PATH_CUSTOM_KEY'])
    thumb_crop_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                           app.config['PATH_CROP_KEY'] /
                           app.config['PATH_CUSTOM_KEY'])
    image = Image.new('RGB', (300, 300), 'green')
    image.save(str(upload_dir.join(pic.value)))
    data = {
        'y1': 0, 'y2': 150,
        'x1': 0, 'x2': 150,
        'w': 150, 'h': 150,
    }

    client = app.test_client()
    with app.test_request_context():
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.custom_field_crop',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)
        resp = app.client.post(url, data=data)
        assert resp.status_code == 302
        assert crop_dir.join(pic.value).check()

        url = url_for('meetings.participant_detail',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id)
        resp = app.client.get(url)
        thumb_name, thumb_fm = os.path.splitext(pic.value)
        thumb_full_name = Thumbnail._get_name(thumb_name, thumb_fm,
                                              '200x200', 85)
        assert thumb_crop_dir.join(thumb_full_name).check()

        url = url_for('meetings.custom_field_upload',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert not crop_dir.join(pic.value).check()
        assert not thumb_crop_dir.join(thumb_full_name).check()


def test_participant_picture_remove_deletes_all_files(app):
    pic = ProfilePictureFactory()
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    crop_dir = local(app.config['UPLOADED_CROP_DEST'] /
                     app.config['PATH_CUSTOM_KEY'])
    thumb_crop_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                           app.config['PATH_CROP_KEY'] /
                           app.config['PATH_CUSTOM_KEY'])
    thumb_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                      app.config['PATH_CUSTOM_KEY'])
    upload_dir.ensure(pic.value)
    crop_dir.ensure(pic.value)
    thumb_name, thumb_fm = os.path.splitext(pic.value)
    thumb_full_name = Thumbnail._get_name(thumb_name, thumb_fm,
                                          '200x200', 85)
    thumb_crop_dir.ensure(thumb_full_name)
    thumb_dir.ensure(thumb_full_name)

    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.custom_field_upload',
                                     meeting_id=pic.custom_field.meeting.id,
                                     participant_id=pic.participant.id,
                                     custom_field_slug='picture'))
        assert resp.status_code == 200
        assert not upload_dir.join(pic.value).check()
        assert not crop_dir.join(pic.value).check()
        assert not thumb_crop_dir.join(thumb_full_name).check()
        assert not thumb_dir.join(thumb_full_name).check()


def test_participant_picture_change_deletes_all_old_files(app):
    pic = ProfilePictureFactory()
    filename = pic.value
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    crop_dir = local(app.config['UPLOADED_CROP_DEST'] /
                     app.config['PATH_CUSTOM_KEY'])
    thumb_crop_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                           app.config['PATH_CROP_KEY'] /
                           app.config['PATH_CUSTOM_KEY'])
    thumb_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                      app.config['PATH_CUSTOM_KEY'])
    upload_dir.ensure(filename)
    crop_dir.ensure(filename)
    thumb_name, thumb_fm = os.path.splitext(filename)
    thumb_full_name = Thumbnail._get_name(thumb_name, thumb_fm,
                                          '200x200', 85)
    thumb_crop_dir.ensure(thumb_full_name)
    thumb_dir.ensure(thumb_full_name)

    data = {'picture': (StringIO('Test'), 'test_edit.png')}
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.custom_field_upload',
                                   meeting_id=pic.custom_field.meeting.id,
                                   participant_id=pic.participant.id,
                                   custom_field_slug='picture'), data=data)
        assert resp.status_code == 200
        assert not upload_dir.join(filename).check()
        assert not crop_dir.join(filename).check()
        assert not thumb_crop_dir.join(thumb_full_name).check()
        assert not thumb_dir.join(thumb_full_name).check()


def test_participant_picture_rotate_deletes_all_old_files(app):
    pic = ProfilePictureFactory()
    filename = pic.value
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    crop_dir = local(app.config['UPLOADED_CROP_DEST'] /
                     app.config['PATH_CUSTOM_KEY'])
    thumb_crop_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                           app.config['PATH_CROP_KEY'] /
                           app.config['PATH_CUSTOM_KEY'])
    thumb_dir = local(app.config['UPLOADED_THUMBNAIL_DEST'] /
                      app.config['PATH_CUSTOM_KEY'])
    image = Image.new('RGB', (250, 250), 'red')
    image.save(str(upload_dir.join(filename)))
    crop_dir.ensure(filename)
    thumb_name, thumb_fm = os.path.splitext(filename)
    thumb_full_name = Thumbnail._get_name(thumb_name, thumb_fm,
                                          '200x200', 85)
    thumb_crop_dir.ensure(thumb_full_name)
    thumb_dir.ensure(thumb_full_name)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.custom_field_rotate',
                      meeting_id=pic.custom_field.meeting.id,
                      participant_id=pic.participant.id,
                      custom_field_slug=pic.custom_field.label.english)

        resp = client.post(url)
        assert resp.status_code == 200
        assert not upload_dir.join(filename).check()
        assert not crop_dir.join(filename).check()
        assert not thumb_crop_dir.join(thumb_full_name).check()
        assert not thumb_dir.join(thumb_full_name).check()
