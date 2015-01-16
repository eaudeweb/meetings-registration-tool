from flask import url_for, g
from pyquery import PyQuery
from py.path import local
from StringIO import StringIO

from mrt.models import Category, Participant
from mrt.pdf import stream_template, PdfRenderer
from mrt.template import url_for_brand_static_path
from mrt.utils import get_meeting_logo
from .factories import MeetingFactory, ParticipantFactory
from .factories import MeetingCategoryFactory


def test_meeting_default_logos(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.statistics',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        logo_src = html('#PRODUCT_LOGO img').attr('src')
        assert logo_src == url_for('brand',
                                   filename=app.config['PRODUCT_LOGO'])
        side_logo_src = html('#PRODUCT_SIDE_LOGO img').attr('src')
        assert side_logo_src == url_for('brand',
                                        filename=app.config['PRODUCT_SIDE_LOGO'])

        remove_buttons = html('.remove-photo.disabled ')
        assert len(remove_buttons) == 2


def test_meeting_custom_logos(app, user):
    meeting = MeetingFactory()
    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    resp = upload_new_logo(app, user, meeting.id,
                           app.config['PRODUCT_LOGO'], left_logo)
    with app.test_request_context():
        left_url = meeting.get_logo(app.config['PRODUCT_LOGO'])
    assert left_url in resp.data
    left_logo_filename = get_meeting_logo(app.config['PRODUCT_LOGO'])
    assert upload_dir.join(left_logo_filename).check()

    resp = upload_new_logo(app, user, meeting.id,
                           app.config['PRODUCT_SIDE_LOGO'], right_logo)
    with app.test_request_context():
        right_url = meeting.get_logo(app.config['PRODUCT_SIDE_LOGO'])
    assert right_url in resp.data
    right_logo_filename = get_meeting_logo(app.config['PRODUCT_SIDE_LOGO'])
    assert upload_dir.join(right_logo_filename).check()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.statistics',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        logo_src = html('#PRODUCT_LOGO a').attr('href')
        assert logo_src == meeting.get_logo(app.config['PRODUCT_LOGO'])
        side_logo_src = html('#PRODUCT_SIDE_LOGO a').attr('href')
        assert side_logo_src == meeting.get_logo(app.config['PRODUCT_SIDE_LOGO'])

        remove_buttons = html('.remove-photo.disabled ')
        assert len(remove_buttons) == 0


def test_meeting_custom_logos_remove(app, user):
    meeting = MeetingFactory()
    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = upload_new_logo(app, user, meeting.id,
                               app.config['PRODUCT_LOGO'], left_logo)
        left_logo_filename = get_meeting_logo(app.config['PRODUCT_LOGO'])
        assert upload_dir.join(left_logo_filename).check()

        resp = client.delete(url_for('meetings.logo_upload',
                                     meeting_id=meeting.id,
                                     logo_slug=app.config['PRODUCT_LOGO']))
        assert resp.status_code == 200
        assert not upload_dir.join(left_logo_filename).check()

        resp = upload_new_logo(app, user, meeting.id,
                               app.config['PRODUCT_SIDE_LOGO'], right_logo)
        right_logo_filename = get_meeting_logo(app.config['PRODUCT_SIDE_LOGO'])
        assert upload_dir.join(right_logo_filename).check()

        resp = client.delete(url_for('meetings.logo_upload',
                                     meeting_id=meeting.id,
                                     logo_slug=app.config['PRODUCT_SIDE_LOGO']))
        assert resp.status_code == 200
        assert not upload_dir.join(right_logo_filename).check()


def test_meeting_left_custom_logo_change_removes_old_logo(app, user):
    meeting = MeetingFactory()
    old_logo = (StringIO('Old'), 'old.png')
    new_logo = (StringIO('new'), 'new.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = upload_new_logo(app, user, meeting.id,
                       app.config['PRODUCT_LOGO'], old_logo)
        old_logo_filename = get_meeting_logo(app.config['PRODUCT_LOGO'])
        assert upload_dir.join(old_logo_filename).check()

        resp = upload_new_logo(app, user, meeting.id,
                       app.config['PRODUCT_LOGO'], new_logo)
        new_logo_filename = get_meeting_logo(app.config['PRODUCT_LOGO'])
        assert upload_dir.join(new_logo_filename).check()
        assert not upload_dir.join(old_logo_filename).check()


def test_meeting_right_custom_logo_change_removes_old_logo(app, user):
    meeting = MeetingFactory()
    old_logo = (StringIO('Old'), 'old.png')
    new_logo = (StringIO('new'), 'new.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = upload_new_logo(app, user, meeting.id,
                       app.config['PRODUCT_SIDE_LOGO'], old_logo)
        old_logo_filename = get_meeting_logo(app.config['PRODUCT_SIDE_LOGO'])
        assert upload_dir.join(old_logo_filename).check()

        resp = upload_new_logo(app, user, meeting.id,
                       app.config['PRODUCT_SIDE_LOGO'], new_logo)
        new_logo_filename = get_meeting_logo(app.config['PRODUCT_SIDE_LOGO'])
        assert upload_dir.join(new_logo_filename).check()
        assert not upload_dir.join(old_logo_filename).check()


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
            url = url_for_brand_static_path(app.config['PRODUCT_LOGO'])
            assert logo.attrib['src'] == url

        side_logos = PyQuery(content)('.side-logo')
        for logo in side_logos:
            url = url_for_brand_static_path(app.config['PRODUCT_SIDE_LOGO'])
            assert logo.attrib['src'] == url


def test_pdf_badge_with_custom_logos(app, user, brand_dir):
    category = MeetingCategoryFactory(category_type=Category.PARTICIPANT)
    ParticipantFactory.create_batch(5, meeting=category.meeting)

    right_logo = (StringIO('Right'), 'right.png')
    left_logo = (StringIO('Left'), 'left.jpg')
    upload_dir = local(app.config['UPLOADED_LOGOS_DEST'])

    upload_new_logo(app, user, category.meeting.id,
                    app.config['PRODUCT_LOGO'], right_logo)
    upload_new_logo(app, user, category.meeting.id,
                    app.config['PRODUCT_SIDE_LOGO'], left_logo)

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
            url = url_for_brand_static_path(app.config['PRODUCT_LOGO'])
            assert logo.attrib['src'] == url

        side_logos = PyQuery(content)('.side-logo')
        for logo in side_logos:
            url = url_for_brand_static_path(app.config['PRODUCT_SIDE_LOGO'])
            assert logo.attrib['src'] == url


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

