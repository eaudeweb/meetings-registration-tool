from flask import url_for
from pyquery import PyQuery
from jinja2 import FileSystemLoader
from werkzeug.datastructures import MultiDict
from sqlalchemy_utils import types
from urllib import urlencode
import xlrd
import json

from .factories import ParticipantFactory, MeetingCategoryFactory
from .factories import CustomFieldFactory, MediaParticipantFactory

from mrt.forms.base import EmailRequired
from mrt.forms.meetings import (add_custom_fields_for_meeting,
                                MediaParticipantDummyForm)
from mrt.mail import mail
from mrt.models import Participant, CustomField, Category
from mrt.utils import translate

from testsuite.utils import populate_participant_form


def test_meeting_participant_list(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED,
                                      category_type=Category.MEDIA)
    MediaParticipantFactory.create_batch(7, category=category)
    ParticipantFactory.create_batch(5, meeting=category.meeting)
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting,
                                      form_class=MediaParticipantDummyForm)
        add_custom_fields_for_meeting(category.meeting)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = {
            'columns[0][data]': 'id',
            'columns[1][data]': 'last_name',
            'columns[2][data]': 'category_id',
            'order[0][column]': 0,
            'order[0][dir]': 'asc'
        }
        url = url_for('meetings.participants_filter',
                      meeting_id=category.meeting.id)
        url = url + '?' + urlencode(data)
        resp = app.client.get(url)
        assert resp.status_code == 200
        resp_data = json.loads(resp.data)
        assert resp_data['recordsTotal'] == 5
        for participant in resp_data['data']:
            assert (Participant.query.get(participant['id']).participant_type
                    == Participant.PARTICIPANT)


def test_meeting_participant_detail(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED)
    meeting = category.meeting
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['diet'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        add_custom_fields_for_meeting(meeting,
                                      form_class=MediaParticipantDummyForm)
        CustomFieldFactory(custom_field_type=CustomField.PARTICIPANT,
                           meeting=meeting, field_type='checkbox',
                           label__english='diet', required=False, sort=30)
        CustomFieldFactory(custom_field_type=CustomField.MEDIA,
                           meeting=meeting, field_type='checkbox')
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=meeting.id), data=data)

        assert resp.status_code == 302
        assert Participant.query.current_meeting().participants().first()
        participant = Participant.query.get(1)
        participant.attended = True
        resp = client.get(url_for('meetings.participant_detail',
                                  meeting_id=category.meeting.id,
                                  participant_id=1))

        assert resp.status_code == 200
        details = PyQuery(resp.data)('tr')
        custom_fields = (
            CustomField.query
            .filter_by(meeting=meeting,
                       custom_field_type=CustomField.PARTICIPANT)
            .order_by(CustomField.sort).all())
        for i, custom_field in enumerate(custom_fields):
            detail_label = details[i].find('th').text_content().strip()
            detail_data = details[i].find('td').text_content().strip()
            try:
                participant_data = getattr(participant, custom_field.slug)
            except AttributeError:
                value = int(custom_field.custom_field_values.first().value)
                participant_data = True if value else False
            assert custom_field.label.english == detail_label
            if isinstance(participant_data, types.choice.Choice):
                assert participant_data.value == detail_data
            elif isinstance(participant_data, types.country.Country):
                assert participant_data.name == detail_data
            elif isinstance(participant_data, bool):
                if participant_data:
                    assert details[i].find('td').find('span') is not None
            elif custom_field.slug == 'category_id':
                assert participant.category.title.english == detail_data
            else:
                assert str(participant_data) == detail_data


def test_meeting_participant_add_success(app, user):
    category = MeetingCategoryFactory()
    meeting = category.meeting
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        add_custom_fields_for_meeting(meeting,
                                      form_class=MediaParticipantDummyForm)
        populate_participant_form(meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=meeting.id), data=data)

        assert resp.status_code == 302
        assert Participant.query.current_meeting().participants().first()
        part = Participant.query.current_meeting().participants().first()
        assert part.participant_type.code == Participant.PARTICIPANT
        assert part.category
        assert part.title
        assert part.language
        assert part.first_name
        assert part.last_name
        assert part.email
        assert part.country


def test_meeting_participant_add_with_custom_field(app, user):
    category = MeetingCategoryFactory()
    CustomFieldFactory(field_type='text', meeting=category.meeting,
                       required=True, label__english='size')
    CustomFieldFactory(field_type='checkbox', meeting=category.meeting,
                       required=True, label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['size'] = 40
    data['passport'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 302
        assert Participant.query.current_meeting().participants().first()


def test_meeting_participant_add_with_multiple_emails_success(app, user):
    category = MeetingCategoryFactory()
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['email'] = 'test@email.com , test2@email.com, test@email.com'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)

        assert resp.status_code == 302
        assert Participant.query.current_meeting().participants().first()


def test_meeting_participant_add_with_multiple_emails_bad_format_fails(app,
                                                                       user):
    category = MeetingCategoryFactory()
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['email'] = 'te st@email.com , test2 @email.com, test@em ail.com'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)

        assert resp.status_code == 200
        error = PyQuery(resp.data)('.text-danger small').text()
        assert error == EmailRequired().message
        assert Participant.query.count() == 0


def test_meeting_participant_add_fail(app, user):
    category = MeetingCategoryFactory()
    CustomFieldFactory(field_type='checkbox', meeting=category.meeting,
                       required=True, label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 200
        assert not Participant.query.current_meeting().participants().first()


def test_meeting_participant_add_form_field_order(app, user):
    category = MeetingCategoryFactory()
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        add_custom_fields_for_meeting(category.meeting,
                                      form_class=MediaParticipantDummyForm)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id

        #CHECK ORDER
        resp = client.get(url_for('meetings.participant_edit',
                                  meeting_id=category.meeting.id), data=data)
        form_fields = PyQuery(resp.data)('.control-label')
        custom_fields = (
            CustomField.query
            .filter_by(meeting=category.meeting, is_primary=True,
                       custom_field_type=CustomField.PARTICIPANT)
            .order_by(CustomField.sort).all())
        for i, custom_field in enumerate(custom_fields):
            assert custom_field.label.english == form_fields[i].text.strip()

        #CHANGE ORDER
        custom_fields[2], custom_fields[3] = custom_fields[3], custom_fields[2]
        new_order = MultiDict([('items[]', x.id) for x in custom_fields])
        resp = client.post(url_for('meetings.custom_field_update_position'),
                           data=new_order)
        assert resp.status_code == 200

        #CHECK ORDER AGAIN
        resp = client.get(url_for('meetings.participant_edit',
                                  meeting_id=category.meeting.id), data=data)
        form_fields = PyQuery(resp.data)('.control-label')
        custom_fields = (
            CustomField.query
            .filter_by(meeting=category.meeting, is_primary=True,
                       custom_field_type=CustomField.PARTICIPANT)
            .order_by(CustomField.sort))
        for i, custom_field in enumerate(custom_fields):
            assert custom_field.label.english == form_fields[i].text.strip()


def test_meeting_participant_edit_form_populated(app, user):
    category = MeetingCategoryFactory()
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)

        assert resp.status_code == 302
        assert Participant.query.current_meeting().participants().first()
        part = Participant.query.current_meeting().participants().first()

        resp = client.get(url_for('meetings.participant_edit',
                                  meeting_id=category.meeting.id,
                                  participant_id=part.id))

        sel = PyQuery(resp.data)

        form_title = sel('#title > option:selected').val()
        form_first_name = sel('#first_name').val()
        form_last_name = sel('#last_name').val()
        form_email = sel('#email').val()
        form_category_id = sel('#category_id input').val()
        form_country = sel('#country > option:selected').val()
        form_language = sel('#language > option:selected').val()
        form_repr_region = sel('#represented_region > option:selected').val()

        assert part.title.code == form_title
        assert part.first_name == form_first_name
        assert part.last_name == form_last_name
        assert part.email == form_email
        assert part.category_id == int(form_category_id)
        assert part.country.code == form_country
        assert part.language.code == form_language
        assert part.represented_region.code == form_repr_region


def test_meeting_participant_delete(app, user):
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert Participant.query.current_meeting().participants().count() == 0


def test_meeting_participant_restore_after_delete(app, user):
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert Participant.query.filter_by(deleted=True).count() == 1

        resp = client.post(url_for('meetings.participant_restore',
                                   meeting_id=part.meeting.id,
                                   participant_id=part.id))
        assert resp.status_code == 200
        assert Participant.query.filter_by(deleted=True).count() == 0


def test_meeting_participant_representing_region(app):
    templates_path = app.config['TEMPLATES_PATH']
    templates_representing = templates_path.ensure_dir(
        'meetings/participant/representing')
    template_name = 'region.html'
    app.jinja_loader = FileSystemLoader(str(templates_path))
    path = (templates_representing / template_name)
    output = '{{ participant.represented_region }}'
    with path.open('w+') as f:
        f.write(output)

    participant = ParticipantFactory()
    assert participant.representing == participant.represented_region.value


def test_meeting_participant_representing_region_translated(app):
    templates_path = app.config['TEMPLATES_PATH']
    templates_representing = templates_path.ensure_dir(
        'meetings/participant/representing')
    template_name = 'region_translated.html'
    app.jinja_loader = FileSystemLoader(str(templates_path))
    path = (templates_representing / template_name)
    output = "{{ participant.represented_region|region_in('fr') }}"
    with path.open('w+') as f:
        f.write(output)

    participant = ParticipantFactory(category__representing=template_name)
    with app.test_request_context():
        assert (translate(participant.represented_region.value, 'fr') ==
                participant.representing)


def test_meeting_participant_acknowledge_email(monkeypatch,
                                               pdf_renderer,
                                               app,
                                               user):
    monkeypatch.setattr('mrt.meetings.participant.PdfRenderer', pdf_renderer)
    part = ParticipantFactory()

    data = {
        'to': part.email,
        'message': 'AckMessage',
        'subject': 'AckSubject',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_acknowledge',
                                   meeting_id=part.meeting.id,
                                   participant_id=part.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 1


def test_meeting_participant_acknowledge_email_with_no_language(monkeypatch,
                                                                pdf_renderer,
                                                                app,
                                                                user):
    monkeypatch.setattr('mrt.meetings.participant.PdfRenderer', pdf_renderer)
    part = ParticipantFactory(language='')

    data = {
        'to': part.email,
        'message': 'AckMessage',
        'subject': 'AckSubject',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_acknowledge',
                                   meeting_id=part.meeting.id,
                                   participant_id=part.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 1


def test_meeting_participants_export_excel(app, user):
    cat = MeetingCategoryFactory()
    participants = ParticipantFactory.stub_batch(10, meeting=cat.meeting,
                                                 category=cat)
    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(cat.meeting)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        for participant in participants:
            data = vars(participant)
            data['category_id'] = cat.id
            populate_participant_form(cat.meeting, data)
            resp = client.post(url_for('meetings.participant_edit',
                                       meeting_id=cat.meeting.id), data=data)
            assert resp.status_code == 302

        resp = client.get(url_for('meetings.participants_export',
                                  meeting_id=cat.meeting.id))
        assert resp.status_code == 200
        excel_filename = app.config['MEDIA_FOLDER'] / 'participants.xls'
        with open(excel_filename, 'wb') as excel_file:
            excel_file.write(resp.data)
        workbook = xlrd.open_workbook(excel_filename)
        for sheet_name in workbook.sheet_names():
            worksheet = workbook.sheet_by_name(sheet_name)
            assert worksheet.nrows == 11
