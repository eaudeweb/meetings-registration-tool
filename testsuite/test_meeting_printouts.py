from flask import url_for
from pyquery import PyQuery
from mrt.utils import slugify

from .factories import ParticipantFactory, MeetingCategoryFactory
from .factories import EventFactory, EventValueFactory


def test_shortlist_printout(app, user):
    cat = MeetingCategoryFactory(sort=1)
    cat_staff = MeetingCategoryFactory(meeting=cat.meeting,
                                       title__english='Staff',
                                       sort=2)
    cat_obs = MeetingCategoryFactory(meeting=cat.meeting,
                                     title__english='Observer',
                                     sort=3)
    categs = [cat, cat_staff, cat_obs]
    ParticipantFactory.create_batch(25, meeting=cat.meeting, category=cat)
    ParticipantFactory.create_batch(25, meeting=cat.meeting,
                                    category=cat_staff)
    ParticipantFactory.create_batch(25, meeting=cat.meeting,
                                    category=cat_obs)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id

        # TEST FIRST PAGE
        resp = client.get(url_for('meetings.printouts_short_list',
                                  meeting_id=cat.meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert len(html('#infinite-scroll-container table tbody tr')) == 52
        groups = html('th.group')
        for group in groups:
            assert categs.pop(0).title.english == group.text.strip()

        participant_names = html('td#participant-name')
        participant_ids = set([x.attrib['data-id'] for x in participant_names])
        assert len(participant_ids) == 50

        # TEST SECOND PAGE
        resp = client.get(url_for('meetings.printouts_short_list',
                                  meeting_id=cat.meeting.id,
                                  page=2))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert len(html('#infinite-scroll-container table tbody tr')) == 26
        category_name = html('th.text-center').pop().text.strip()
        assert categs.pop().title.english == category_name
        participant_names = html('td#participant-name')
        for participant in participant_names:
            participant_ids.add(participant.attrib['data-id'])
        assert len(participant_ids) == 75

        # TEST 404 PAGE
        resp = client.get(url_for('meetings.printouts_short_list',
                                  meeting_id=cat.meeting.id,
                                  page=3))
        assert resp.status_code == 404


def test_event_list_printout(app, user):
    category = MeetingCategoryFactory()
    first_event = EventFactory(meeting=category.meeting,
                               label__english='First event')
    second_event = EventFactory(meeting=category.meeting,
                                label__english='Second event')
    EventValueFactory.create_batch(5, custom_field=first_event,
                                   participant__category=category)
    EventValueFactory.create_batch(7, custom_field=second_event,
                                   participant__category=category)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id

        resp = client.get(url_for('meetings.printouts_participant_events',
                                  meeting_id=category.meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 14

        resp = client.get(url_for('meetings.printouts_participant_events',
                                  meeting_id=category.meeting.id,
                                  events=first_event.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 6

        resp = client.get(url_for('meetings.printouts_participant_events',
                                  meeting_id=category.meeting.id,
                                  events=second_event.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 8

def test_distribution_of_documents_printout(app, user):
    category_default = MeetingCategoryFactory(sort=1)
    meeting = category_default.meeting
    category_staff = MeetingCategoryFactory(meeting=meeting,
                                     title__english='Staff',
                                     sort=2)
    category_observer = MeetingCategoryFactory(meeting=meeting,
                                     title__english='Observer',
                                     sort=3)
    categories = [category_default, category_staff, category_observer]

    for lang in ['English', 'French', 'Spanish']:
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_default, language=unicode(lang))
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_default, language=unicode(lang), represented_region=u'Africa')
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_staff, language=unicode(lang))
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_staff, language=unicode(lang), represented_region=u'Africa')
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_observer, language=unicode(lang))
        ParticipantFactory.create_batch(5, meeting=meeting, category=category_observer, language=unicode(lang), represented_region=u'Africa')

    client = app.test_client()

    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id

        resp = client.get(url_for('meetings.printouts_document_distribution',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)

        # Test each part
        for lang in ['english', 'french', 'spanish']:
            assert len(html('#english-container tbody tr')) == 9

            representings = list(x.attrib['data-id'] for x in html('#english-container tbody tr td#representing-name'))
            assert representings.count('africa') is 3
            assert representings.count('asia') is 3

            category_ids = list(x.attrib['data-id'] for x in html('#%s-container tbody tr th#category-name' % lang))
            # Test that categories order on the page respects categories sort order
            assert slugify(categories[0].title.english) == category_ids[0] and \
                slugify(categories[1].title.english) == category_ids[1] and \
                slugify(categories[2].title.english) == category_ids[2]
            for category in categories:
                assert slugify(category.title.english) in category_ids

            assert len(category_ids) is len(categories)
