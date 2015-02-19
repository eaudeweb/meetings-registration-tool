from flask import url_for, g
from pyquery import PyQuery
from py.path import local
from StringIO import StringIO

from mrt.models import Category, Participant
from mrt.pdf import PdfRenderer
from mrt.utils import Logo
from .factories import MeetingFactory, ParticipantFactory
from .factories import MeetingCategoryFactory


def test_meeting_default_logos(app, user, brand_dir):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        product_logo = Logo('product_logo')
        product_side_logo = Logo('product_side_logo')

        resp = client.get(url_for('meetings.logos', meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        logo_src = html('#PRODUCT_LOGO img').attr('src')
        assert logo_src == product_logo.url
        side_logo_src = html('#PRODUCT_SIDE_LOGO img').attr('src')
        assert side_logo_src == product_side_logo.url

        remove_buttons = html('.remove-photo')
        assert len(remove_buttons) == 2
        for button in remove_buttons:
            assert 'display: none' in button.attrib['style']


def test_meeting_custom_logos(app, user, brand_dir):
    meeting = MeetingFactory()
    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    with app.test_request_context():
        resp = upload_new_logo(app, user, meeting.id, 'PRODUCT_LOGO', left_logo)
        product_logo = Logo('product_logo')

        assert product_logo.url in resp.data
        assert upload_dir.join(product_logo.filename).check()

        resp = upload_new_logo(app, user, meeting.id, 'PRODUCT_SIDE_LOGO',
                               right_logo)
        product_side_logo = Logo('product_side_logo')

        assert product_side_logo.url in resp.data
        assert upload_dir.join(product_side_logo.filename).check()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.logos', meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        logo_src = html('#PRODUCT_LOGO a').attr('href')
        assert logo_src == product_logo.url
        side_logo_src = html('#PRODUCT_SIDE_LOGO a').attr('href')
        assert side_logo_src == product_side_logo.url

        remove_buttons = html('.remove-photo.disabled ')
        assert len(remove_buttons) == 0


def test_meeting_custom_logos_remove(app, user, brand_dir):
    meeting = MeetingFactory()
    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        product_logo = Logo('product_logo')
        product_side_logo = Logo('product_side_logo')

        resp = upload_new_logo(app, user, meeting.id, 'PRODUCT_LOGO', left_logo)
        assert upload_dir.join(product_logo.filename).check()

        resp = client.delete(url_for('meetings.logo_upload',
                                     meeting_id=meeting.id,
                                     logo_slug='PRODUCT_LOGO'))
        assert resp.status_code == 200
        assert not upload_dir.join(product_logo.filename).check()

        resp = upload_new_logo(app, user, meeting.id, 'PRODUCT_SIDE_LOGO',
                               right_logo)
        right_logo_filename = product_side_logo.filename
        assert upload_dir.join(right_logo_filename).check()

        resp = client.delete(url_for('meetings.logo_upload',
                                     meeting_id=meeting.id,
                                     logo_slug='PRODUCT_SIDE_LOGO'))
        assert resp.status_code == 200
        assert not upload_dir.join(right_logo_filename).check()


def test_meeting_left_custom_logo_change_removes_old_logo(app, user, brand_dir):
    meeting = MeetingFactory()
    old_logo = (StringIO('Old'), 'old.png')
    new_file_content = 'New!'
    new_logo = (StringIO(new_file_content), 'new.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        product_logo = Logo('product_logo')

        upload_new_logo(app, user, meeting.id, 'PRODUCT_LOGO', old_logo)
        old_file = upload_dir.join(product_logo.filename)
        assert old_file.check()
        old_file_content = old_file.read()

        upload_new_logo(app, user, meeting.id, 'PRODUCT_LOGO', new_logo)
        new_file = upload_dir.join(product_logo.filename)
        assert new_file.check()
        assert new_file.read() != old_file_content
        assert new_file.read() == new_file_content


def test_meeting_right_custom_logo_change_removes_old_logo(app, user,
                                                           brand_dir):
    meeting = MeetingFactory()
    old_logo = (StringIO('Old'), 'old.png')
    new_file_content = 'New!'
    new_logo = (StringIO(new_file_content), 'new.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        product_side_logo = Logo('product_side_logo')

        upload_new_logo(app, user, meeting.id, 'PRODUCT_SIDE_LOGO', old_logo)
        old_file = upload_dir.join(product_side_logo.filename)
        assert old_file.check()
        old_file_content = old_file.read()

        upload_new_logo(app, user, meeting.id, 'PRODUCT_SIDE_LOGO', new_logo)
        new_file = upload_dir.join(product_side_logo.filename)
        assert new_file.check()
        assert new_file.read() != old_file_content
        assert new_file.read() == new_file_content


def test_pdf_badge_with_default_logos(app, brand_dir):
    category = MeetingCategoryFactory(category_type=Category.PARTICIPANT)
    ParticipantFactory.create_batch(5, meeting=category.meeting)

    g.meeting = category.meeting
    participants = Participant.query.all()
    context = {'participants': participants}
    renderer = PdfRenderer('meetings/printouts/badges_pdf.html',
                           height='2.15in', width='3.4in', context=context)
    renderer._render_template()

    with open(renderer.template_path, 'r') as content_file:
        content = content_file.read()
        product_logos = PyQuery(content)('.logo')
        for logo in product_logos:
            assert logo.attrib['src'] == Logo('PRODUCT_LOGO').url

        side_logos = PyQuery(content)('.side-logo')
        for logo in side_logos:
            assert logo.attrib['src'] == Logo('PRODUCT_SIDE_LOGO').url


def test_pdf_badge_with_custom_logos(app, user, brand_dir):
    category = MeetingCategoryFactory(category_type=Category.PARTICIPANT)
    ParticipantFactory.create_batch(5, meeting=category.meeting)

    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')

    upload_new_logo(app, user, category.meeting.id, 'PRODUCT_LOGO', right_logo)
    upload_new_logo(app, user, category.meeting.id, 'PRODUCT_SIDE_LOGO',
                    left_logo)

    g.meeting = category.meeting
    participants = Participant.query.all()
    context = {'participants': participants}
    renderer = PdfRenderer('meetings/printouts/badges_pdf.html',
                           height='2.15in', width='3.4in', context=context)
    renderer._render_template()

    with open(renderer.template_path, 'r') as content_file:
        content = content_file.read()
        product_logos = PyQuery(content)('.logo')
        for logo in product_logos:
            assert logo.attrib['src'] == Logo('PRODUCT_LOGO').url

        side_logos = PyQuery(content)('.side-logo')
        for logo in side_logos:
            assert logo.attrib['src'] == Logo('PRODUCT_SIDE_LOGO').url


def upload_new_logo(app, user, meeting_id, logo_slug, new_logo):
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.logo_upload',
                                   meeting_id=meeting_id,
                                   logo_slug=logo_slug),
                           data={'logo': new_logo})
        assert resp.status_code == 200
        return resp
