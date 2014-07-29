from flask import url_for
from pyquery import PyQuery

from .factories import PhraseDefaultFactory
from mrt.definitions import MEETING_TYPES


def test_default_phrase_types_list(app):
    client = app.test_client()
    with app.test_request_context():
        resp = client.get(url_for('admin.phrases'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == len(MEETING_TYPES)


def test_default_phrase_category_list(app):
    PhraseDefaultFactory.create_batch(5)
    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.phrase_edit', meeting_type='cop')
        resp = client.get(url, follow_redirects=True)
        assert resp.status_code == 200
        phrases = PyQuery(resp.data)('ul.nav-pills li')
        assert len(phrases) == 6


def test_default_phrase_edit_successfully(app):
    phrase = PhraseDefaultFactory()
    data = PhraseDefaultFactory.attributes()
    data['description-english'] = 'Enter credentials'
    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
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
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.text-danger')
        assert len(alert) == 1
