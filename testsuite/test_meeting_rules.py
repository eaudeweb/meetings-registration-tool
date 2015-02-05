from flask import url_for
from pyquery import PyQuery
from StringIO import StringIO

from mrt.forms.meetings import add_custom_fields_for_meeting
from mrt.models import Rule, Condition, ConditionValue, Action
from .factories import ConditionValueFactory, ActionFactory, MeetingFactory
from .factories import CustomFieldFactory, MeetingCategoryFactory
from .factories import ParticipantFactory
from .test_meeting_registration import register_participant_online


def test_meeting_rules_list(app, user):
    meeting = MeetingFactory()
    for x in range(5):
        _create_new_rule(meeting, x)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.rules',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 5


def test_meeting_rule_add_success(app, user):
    category = MeetingCategoryFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(category.meeting)
        data = _create_simple_rule_data(category.meeting)
        resp = client.post(url_for('meetings.rule_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 302
        assert Rule.query.count() == 1


def test_meeting_rule_add_fail_action_field_is_cond_field(app, user):
    category = MeetingCategoryFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(category.meeting)
        data = _create_simple_rule_data(category.meeting)
        data['conditions-0-field'] = data['actions-0-field']
        resp = client.post(url_for('meetings.rule_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 200
        assert Rule.query.count() == 0
        error = PyQuery(resp.data)('div.alert-danger')
        assert len(error) == 1


def test_meeting_rule_add_fail_same_action_field_twice(app, user):
    category = MeetingCategoryFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(category.meeting)
        data = _create_simple_rule_data(category.meeting)
        data['actions-1-field'] = data['actions-0-field']
        resp = client.post(url_for('meetings.rule_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 200
        assert Rule.query.count() == 0
        error = PyQuery(resp.data)('div.alert-danger')
        assert len(error) == 1


def test_meeting_rule_delete(app, user):
    meeting = MeetingFactory()
    rule = _create_new_rule(meeting, 0)
    assert Rule.query.count() == 1

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.rule_edit',
                                     meeting_id=meeting.id, rule_id=rule.id))
        assert resp.status_code == 200
        assert Rule.query.count() == 0
        assert Condition.query.count() == 0
        assert ConditionValue.query.count() == 0
        assert Action.query.count() == 0


def test_meeting_rule_on_registration(app, user, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(meeting)
        fields = meeting.custom_fields
        cond_field = fields.filter_by(slug='category_id').one()
        action_field = fields.filter_by(slug='represented_organization').one()
        cond_value = ConditionValueFactory(condition__rule__meeting=meeting,
                                           condition__field=cond_field,
                                           value=category.id)
        ActionFactory(rule=cond_value.condition.rule, field=action_field,
                      is_required=True)
        assert Rule.query.count() == 1

        data = ParticipantFactory.attributes()
        data['category_id'] = category.id
        resp = register_participant_online(client, data, meeting)
        errors = PyQuery(resp.data)('div.text-danger')
        assert len(errors) == 1
        assert meeting.participants.count() == 0


def test_meeting_complex_rule_on_registration(app, user, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    birth_field = CustomFieldFactory(label__english='Place of birth',
                                     meeting=meeting,
                                     field_type='country')
    passport_field = CustomFieldFactory(label__english='Passport Photo',
                                        meeting=meeting,
                                        required=False)
    info_field = CustomFieldFactory(label__english='Extra info',
                                    meeting=meeting,
                                    field_type='text',
                                    required=False)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(meeting)
        fields = meeting.custom_fields
        country_field = fields.filter_by(slug='country').one()
        category_field = fields.filter_by(slug='category_id').one()
        country_cond = ConditionValueFactory(condition__rule__meeting=meeting,
                                             condition__field=country_field,
                                             value='RO')
        ConditionValueFactory(condition__rule=country_cond.condition.rule,
                              condition__field=category_field,
                              value=category.id)
        ConditionValueFactory(condition__rule=country_cond.condition.rule,
                              condition__field=birth_field,
                              value='AZ')
        ActionFactory(rule=country_cond.condition.rule,
                      field=passport_field,
                      is_required=True)
        ActionFactory(rule=country_cond.condition.rule,
                      field=info_field,
                      is_required=True)

        data = ParticipantFactory.attributes()
        data['category_id'] = category.id
        data['country'] = 'RO'
        data[birth_field.slug] = 'AZ'
        resp = register_participant_online(client, data, meeting)
        errors = PyQuery(resp.data)('div.text-danger')
        assert len(errors) == 2
        assert meeting.participants.count() == 0

        data[passport_field.slug] = (StringIO('Test'), 'test.png')
        data[info_field.slug] = 'Extra info about participant'
        resp = register_participant_online(client, data, meeting)
        errors = PyQuery(resp.data)('div.text-danger')
        assert len(errors) == 0
        assert meeting.participants.count() == 1


def _create_new_rule(meeting, field_id):
    field = CustomFieldFactory(label__english='field' + str(field_id))
    condition_value = ConditionValueFactory(condition__rule__meeting=meeting,
                                            condition__field=field)
    condition = condition_value.condition
    ActionFactory(rule=condition.rule, field=condition.field)
    return condition.rule


def _create_simple_rule_data(meeting):
    action_field = CustomFieldFactory(label__english='Place of birth',
                                      field_type='country',
                                      meeting=meeting,
                                      required=False,
                                      visible_on_registration_form=True)
    cond_field = meeting.custom_fields.filter_by(slug='category_id').scalar()
    data = {
        'name': 'First Rule',
        'actions-0-is_visible': 'y',
        'actions-0-is_required': 'y',
        'actions-0-field': action_field.id,
        'conditions-0-field': cond_field.id,
        'conditions-0-values': meeting.categories.first().id
    }
    return data
