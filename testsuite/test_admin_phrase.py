from flask import url_for
from pyquery import PyQuery

from .factories import PhraseDefaultFactory
from mrt.definitions import MEETING_TYPES


def test_default_phrase_types_list(app):
    client = app.test_client()
    with app.test_request_context():
        resp = client.get(url_for('admin.phrases'))
        tbody = PyQuery(resp.data)('#types')('tbody')
        row_count = len(tbody('tr'))
        assert resp.status_code == 200
        assert row_count == len(MEETING_TYPES)


def test_default_phrase_category_list(app):
    PhraseDefaultFactory.create_batch(5)
    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.phrase_edit', meeting_type='cop')
        resp = client.get(url, follow_redirects=True)
        group = PyQuery(resp.data)('ul.nav-pills')
        phrases_count = len(group('li'))
        assert resp.status_code == 200
        assert phrases_count == 6


def test_default_phrase_edit_successfully(app):
    phrase = PhraseDefaultFactory()
    data = PhraseDefaultFactory.attributes()
    data['description-english'] = 'Enter credentials'
    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1


def test_default_phrase_edit_fail(app):
    phrase = PhraseDefaultFactory()
    data = PhraseDefaultFactory.attributes()
    data['description-english'] = 'Enter credentials'
    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        danger = PyQuery(resp.data)('.text-danger')
        assert len(danger) == 1
