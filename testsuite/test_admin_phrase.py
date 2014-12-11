from flask import url_for
from pyquery import PyQuery

from .factories import (
    PhraseDefaultFactory, RoleUserFactory, MeetingTypeFactory,
)


PERMISSION = ('manage_default', )


def test_default_phrase_types_list(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    client = app.test_client()
    MeetingTypeFactory.create_batch(5)
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.get(url_for('admin.phrases'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 5


def test_default_phrase_category_list(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    meeting_type = MeetingTypeFactory(slug='cop')
    PhraseDefaultFactory.create_batch(5, meeting_type=meeting_type)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.phrase_edit', meeting_type='cop')
        resp = client.get(url, follow_redirects=True)
        assert resp.status_code == 200
        phrases = PyQuery(resp.data)('ul.nav-pills li')
        assert len(phrases) == 6


def test_default_phrase_edit_successfully(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    phrase = PhraseDefaultFactory()
    data = PhraseDefaultFactory.attributes()
    data['description-english'] = descr = 'Enter credentials'
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1
        assert phrase.description.english == descr


def test_default_phrase_edit_fail(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    phrase = PhraseDefaultFactory()
    data = PhraseDefaultFactory.attributes()
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.text-danger')
        assert len(alert) == 2
