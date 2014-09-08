from flask import url_for
from jinja2 import FileSystemLoader

from .factories import ParticipantFactory, RoleUserFactory, StaffFactory
from .factories import MeetingCategoryFactory, RoleUserMeetingFactory
from .factories import CustomFieldFactory

from mrt.models import Participant
from mrt.utils import translate


def test_meeting_participant_add_success(app):
    category = MeetingCategoryFactory()
    role_user = RoleUserMeetingFactory(meeting=category.meeting)
    StaffFactory(user=role_user.user)
    CustomFieldFactory(field_type='checkbox', meeting=category.meeting,
                       required=True, label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['passport'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 302
        assert Participant.query.filter_by(meeting=category.meeting).first()


def test_meeting_participant_add_fail(app):
    category = MeetingCategoryFactory()
    role_user = RoleUserMeetingFactory(meeting=category.meeting)
    StaffFactory(user=role_user.user)
    CustomFieldFactory(field_type='checkbox', meeting=category.meeting,
                       required=True, label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 200
        assert not category.meeting.participants.first()


def test_meeting_participant_delete(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert part.meeting.participants.filter_by(deleted=False).count() == 0


def test_meeting_participant_restore_after_delete(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert part.meeting.participants.filter_by(deleted=True).count() == 1

        resp = client.post(url_for('meetings.participant_restore',
                                   meeting_id=part.meeting.id,
                                   participant_id=part.id))
        assert resp.status_code == 200
        assert part.meeting.participants.filter_by(deleted=True).count() == 0


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
