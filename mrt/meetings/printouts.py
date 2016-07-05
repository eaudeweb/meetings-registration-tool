from datetime import datetime
from itertools import groupby
from operator import attrgetter

from flask import current_app as app
from flask import g, flash, url_for
from flask import request, render_template, jsonify, abort, redirect
from flask import send_from_directory
from flask.ext.login import login_required, current_user
from flask.views import MethodView

from rq import Queue, Connection
from rq.job import Job as JobRedis
from rq.job import NoSuchJobError
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from sqlalchemy_utils.types.country import Country

from mrt.forms.meetings import BadgeCategories, EventsForm
from mrt.forms.meetings import FlagForm, CategoryTagForm, MediaCategoriesForm
from mrt.forms.meetings import ParticipantCategoriesForm
from mrt.models import Participant, Category, CategoryTag, Meeting, Job
from mrt.models import redis_store, db, CustomFieldValue, CustomField
from mrt.models import get_participants_full
from mrt.pdf import PdfRenderer
from mrt.template import pluralize
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.utils import generate_excel


_PRINTOUT_MARGIN = {'top': '0.5in', 'bottom': '0.5in', 'left': '0.8in',
                    'right': '0.8in'}


def _add_to_printout_queue(method, job_name, *args):
    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    job_redis = q.enqueue(method, g.meeting.id, *args)
    job = Job(id=job_redis.id,
              name=job_name,
              user_id=current_user.id,
              status=job_redis.get_status(),
              date=job_redis.enqueued_at,
              meeting_id=g.meeting.id,
              queue=Job.PRINTOUTS_QUEUE)
    db.session.add(job)
    db.session.commit()
    url = url_for('.processing_file_list')
    flash('Started processing %s. You can see the progress in the '
          '<a href="%s">processing file list section</a>.' %
          (job_name, url), 'success')


class ProcessingFileList(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    def get(self):
        page = request.args.get('page', 1, type=int)
        jobs = Job.query.filter_by(meeting=g.meeting).order_by(desc(Job.date))
        jobs = jobs.paginate(page, per_page=50)
        return render_template('meetings/printouts/processing_file_list.html',
                               jobs=jobs)


class Badges(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    JOB_NAME = 'participant categories'

    def get(self):
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        flag = request.args.get('flag')
        participants = Participant.query.current_meeting().participants()
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        if flag:
            attr = getattr(Participant, flag)
            participants = participants.filter(attr == True)
        badge_categories_form = BadgeCategories(request.args)
        participants = participants.paginate(page, per_page=50)
        return render_template('meetings/printouts/badges.html',
                               participants=participants,
                               category_ids=category_ids,
                               flag=flag,
                               badge_categories_form=badge_categories_form)

    def post(self):
        category_ids = request.args.getlist('categories')
        size = request.form.get('printout_size', 'default')
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_badges, self.JOB_NAME,
                               flag, size, category_ids)
        return redirect(url_for('.printouts_participant_badges',
                                categories=category_ids, flag=flag))


def _process_badges(meeting_id, flag, size, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    participants = Participant.query.current_meeting().participants()
    if category_ids:
        participants = participants.filter(
            Participant.category.has(Category.id.in_(category_ids))
        )
    if flag:
            attr = getattr(Participant, flag)
            participants = participants.filter(attr == True)
    context = {'participants': participants, 'printout_size': size}
    w, h = ('8.3in', '11.7in') if size == 'A4' else ('3.4in', '2.15in')
    return PdfRenderer('meetings/printouts/badges_pdf.html',
                       width=w, height=h, orientation='portrait',
                       footer=False, context=context).as_rq()


class JobStatus(MethodView):

    decorators = (login_required,)

    def get(self):
        job_id = request.args['job_id']
        job = Job.query.get_or_404(job_id)

        with Connection(redis_store._redis_client):
            try:
                job_redis = JobRedis.fetch(job.id)
            except NoSuchJobError:
                job.status = Job.FAILED
                db.session.commit()
                abort(404)

            if job_redis.is_finished:
                result = {'status': job_redis.get_status(),
                          'result': job_redis.result}
            else:
                result = {'status': job_redis.get_status()}

            job.status = job_redis.get_status()
            job.result = job_redis.result
            db.session.commit()
            return jsonify(**result)


class QueueStatus(MethodView):

    decorators = (login_required,)

    def get(self, queue):
        jobs = Job.query.filter_by(queue=queue, status=Job.QUEUED)
        count = jobs.count()
        title = '%d processing job%s' % (count, pluralize(count))
        return jsonify(count=count, title=title)


class PDFDownload(MethodView):

    decorators = (login_required,)

    def get(self, filename):
        return send_from_directory(app.config['UPLOADED_PRINTOUTS_DEST'],
                                   filename)


class ShortList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'short list'
    DOC_TITLE = 'List of participants'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Category.id,
                      Participant.last_name, Participant.id)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = groupby(pagination.items, key=attrgetter('category'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/short_list.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_short_list, self.JOB_NAME,
                               self.DOC_TITLE, flag)
        return redirect(url_for('.printouts_short_list', flag=flag))


class ProvisionalList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'participant list'
    DOC_TITLE = 'Provisional list as entered by participant'
    TITLE_MAP = {
        'attended': 'Final list of participants',
        'verified': 'List of acknowledged participants',
        'credentials': 'List of participants with checked credentials',
    }

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Category.id,
                      Participant.representing,
                      Participant.last_name, Participant.id)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        title = self.TITLE_MAP.get(flag, self.DOC_TITLE)
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/provisional_list.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=title,
            flag_form=flag_form,
            flag=flag)

    def post(self):
        flag = request.args.get('flag')
        title = self.TITLE_MAP.get(flag, self.DOC_TITLE)
        _add_to_printout_queue(_process_provisional_list, self.JOB_NAME,
                               title, flag)
        return redirect(url_for('.printouts_provisional_list', flag=flag))


class DelegationsList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'delegation list'
    DOC_TITLE = 'List of delegations (to prepare the meeting room)'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Category.id,
                      Participant.last_name, Participant.id)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        query = self._get_query(flag)
        participants = groupby(query, key=attrgetter('category'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/delegation_list.html',
            participants=participants,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_delegation_list, self.JOB_NAME,
                               self.DOC_TITLE, flag)
        return redirect(url_for('.printouts_delegation_list', flag=flag))


class EventList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'event list'
    DOC_TITLE = 'List of announced participants in events'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(event_ids):
        query = (
            CustomFieldValue.query.filter(
                CustomFieldValue.participant.has(meeting_id=g.meeting.id),
                CustomFieldValue.custom_field.has(field_type='event'),
                CustomFieldValue.value == 'true')
            .order_by(CustomFieldValue.custom_field_id))

        if event_ids:
            query = (
                query.filter(CustomFieldValue.custom_field.has(
                    CustomField.id.in_(event_ids))))

        return query

    def get(self):
        event_ids = request.args.getlist('events')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(event_ids)
        count = query.count()

        pagination = query.paginate(page, per_page=50)
        participants = groupby(pagination.items,
                               key=attrgetter('custom_field'))
        event_form = EventsForm(request.args)
        return render_template(
            'meetings/printouts/event_list.html',
            participants=participants,
            count=count,
            title=self.DOC_TITLE,
            event_ids=event_ids,
            event_form=event_form,
            pagination=pagination)

    def post(self):
        event_ids = request.args.getlist('events')
        _add_to_printout_queue(_process_event_list, self.JOB_NAME,
                               self.DOC_TITLE, event_ids)
        return redirect(url_for('.printouts_participant_events',
                                events=event_ids))


class BaseDistribution(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Participant.language, Category.sort)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        query = self._get_query(flag)
        count = query.count()
        participants = groupby(query, key=attrgetter('language'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()

        return render_template(
            'meetings/printouts/distribution.html',
            printout_type=self.printout_type,
            participants=participants,
            count=count,
            title=self.DOC_TITLE,
            table_class=self.table_class,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_distribution, self.JOB_NAME,
                               self.printout_type, self.DOC_TITLE, flag)
        return redirect(url_for(self.view_name, flag=flag))


class DocumentDistribution(BaseDistribution):

    JOB_NAME = 'document distribution'
    DOC_TITLE = 'Distribution of documents'

    template = 'meetings/printouts/distribution.html'
    view_name = '.printouts_document_distribution'
    printout_type = 'distribution'
    table_class = 'table-bordered table-condensed'


class PigeonHoles(BaseDistribution):

    JOB_NAME = 'pigeon holes'
    DOC_TITLE = 'Pigeon holes'

    template = 'meetings/printouts/distribution.html'
    view_name = '.printouts_pigeon_holes'
    printout_type = 'pigeon'
    table_class = 'pigeon-holes'


class Admission(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'admission'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_tags):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Category.id)
        )

        category_ids = []
        for tag in category_tags:
            category_ids += [category.id for category in
                tag.categories.filter_by(meeting_id=g.meeting.id)]

        if category_tags:
            query = query.filter(Participant.category_id.in_(category_ids))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        category_tags = (CategoryTag.query
                         .filter(CategoryTag.id.in_(category_tags))
                         .all())
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag, category_tags)
        count = query.count()
        pagination = query.paginate(page, per_page=1000)
        participants = pagination.items
        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        if not category_tags:
            title = 'General admission'
        else:
            title = (', '.join([tag.label for tag in category_tags])
                + ' admission')
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()

        return render_template(
            'meetings/printouts/admission.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=title,
            flag=flag,
            flag_form=flag_form,
            category_tags_form=category_tags_form)

    def post(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        _add_to_printout_queue(_process_admission, self.JOB_NAME, flag,
                                category_tags)
        return redirect(url_for('.printouts_admission', flag=flag,
                                category_tags=category_tags))


class Credentials(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'credentials'
    DOC_TITLE = 'List of credentials'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_tags):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Category.id)
            .order_by(Participant.representing)
            .order_by(Participant.last_name)
        )

        category_ids = []
        for tag in category_tags:
            category_ids += [category.id for category in
                tag.categories.filter_by(meeting_id=g.meeting.id)]

        if category_tags:
            query = query.filter(Participant.category_id.in_(category_ids))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag_slug = request.args.get('flag')
        category_tag_ids = request.args.getlist('category_tags')
        category_tags = (CategoryTag.query
                         .filter(CategoryTag.id.in_(category_tag_ids))
                         .all())
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag_slug, category_tags)
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items
        flag_form = FlagForm(request.args)
        flag_form.flag.choices = [
            choice for choice in flag_form.flag.choices if choice[0] != 'credentials']
        category_tags_form = CategoryTagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag_slug).first()

        return render_template(
            'meetings/printouts/credentials.html',
            participants=participants,
            pagination=pagination,
            title=self.DOC_TITLE,
            flag=flag,
            flag_slug=flag_slug,
            flag_form=flag_form,
            category_tag_ids=category_tag_ids,
            category_tags_form=category_tags_form)

    def post(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        _add_to_printout_queue(_process_credentials, self.JOB_NAME,
                               self.DOC_TITLE, flag, category_tags)
        return redirect(url_for('.printouts_credentials', flag=flag,
                                category_tags=category_tags))


class MediaList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'media list'
    DOC_TITLE = 'List of media participants'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_ids):

        query = (
            Participant.query.current_meeting().media_participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Category.id)
            .order_by(Participant.last_name)
        )

        if category_ids:
            query = query.filter(Participant.category_id.in_(category_ids))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag_slug = request.args.get('flag')
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag_slug, category_ids)
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items
        flag_form = FlagForm(request.args)
        flag_form.flag.choices = [
            choice for choice in flag_form.flag.choices if choice[0] != 'credentials']
        categories_form = MediaCategoriesForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag_slug).first()

        return render_template(
            'meetings/printouts/media.html',
            participants=participants,
            pagination=pagination,
            title=self.DOC_TITLE,
            flag=flag,
            flag_slug=flag_slug,
            flag_form=flag_form,
            category_ids=category_ids,
            categories_form=categories_form)

    def post(self):
        flag = request.args.get('flag')
        category_ids = request.args.getlist('categories')
        _add_to_printout_queue(_process_media, self.JOB_NAME,
                               self.DOC_TITLE, flag, category_ids)
        return redirect(url_for('.printouts_media', flag=flag,
                                categories=category_ids))


class VerificationList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'verification list'
    DOC_TITLE = 'List of participants for verification'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(category_ids):

        query = (
            Participant.query.current_meeting().participants()
            .filter_by(attended=True)
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Category.id)
            .order_by(Participant.representing)
            .order_by(Participant.last_name)
        )

        if category_ids:
            query = query.filter(Participant.category_id.in_(category_ids))

        return query

    def get(self):
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(category_ids)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items
        categories_form = ParticipantCategoriesForm(request.args)

        return render_template(
            'meetings/printouts/verification.html',
            participants=participants,
            pagination=pagination,
            title=self.DOC_TITLE,
            count=count,
            category_ids=category_ids,
            categories_form=categories_form)

    def post(self):
        category_ids = request.args.getlist('categories')
        _add_to_printout_queue(_process_verification, self.JOB_NAME,
                               self.DOC_TITLE, category_ids)
        return redirect(url_for('.printouts_verification',
                                categories=category_ids))


class PartiesList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'announced parties'
    DOC_TITLE = 'List of announced Parties (by country)'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_tags, categories):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Participant.represented_country)
            .order_by(Participant.last_name)
        )

        if category_tags and not categories:
            categories = (
                g.meeting.categories
                .filter(Category.tags.any(CategoryTag.id.in_(category_tags)))
                .with_entities('id'))

        if categories:
            query = query.filter(Participant.category_id.in_(categories))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        categories = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)

        events = g.meeting.custom_fields.filter_by(field_type=CustomField.EVENT)

        query = self._get_query(flag, category_tags, categories)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items

        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        categories_form = ParticipantCategoriesForm(request.args)

        return render_template(
            'meetings/printouts/parties.html',
            participants=participants,
            events=events,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form,
            category_tags=category_tags,
            category_tags_form=category_tags_form,
            categories=categories,
            categories_form=categories_form,
        )

    def post(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        categories = request.args.getlist('categories')
        _add_to_printout_queue(_process_parties, self.JOB_NAME, self.DOC_TITLE,
                               flag, category_tags, categories)
        return redirect(url_for('.printouts_parties', flag=flag,
                                category_tags=category_tags,
                                categories=categories))


class ObserversList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'announced observers'
    DOC_TITLE = 'List of announced observers (by organization)'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_tags, categories):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Participant.last_name)
        )

        if category_tags and not categories:
            categories = (
                g.meeting.categories
                .filter(Category.tags.any(CategoryTag.id.in_(category_tags)))
                .with_entities('id'))

        if categories:
            query = query.filter(Participant.category_id.in_(categories))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        categories = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)

        events = g.meeting.custom_fields.filter_by(field_type=CustomField.EVENT)

        query = self._get_query(flag, category_tags, categories)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items

        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        categories_form = ParticipantCategoriesForm(request.args)

        return render_template(
            'meetings/printouts/observers.html',
            participants=participants,
            events=events,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form,
            category_tags=category_tags,
            category_tags_form=category_tags_form,
            categories=categories,
            categories_form=categories_form,
        )

    def post(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        categories = request.args.getlist('categories')
        _add_to_printout_queue(_process_observers, self.JOB_NAME, self.DOC_TITLE,
                               flag, category_tags, categories)
        return redirect(url_for('.printouts_observers', flag=flag,
                                category_tags=category_tags,
                                categories=categories))


class PrintoutFooter(MethodView):

    def get(self):
        return render_template('meetings/printouts/footer.html',
                               now=datetime.now())


def _process_short_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = ShortList._get_query(flag)
    count = query.count()
    participants = groupby(query, key=attrgetter('category'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'count': count,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_short_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_provisional_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = ProvisionalList._get_query(flag)
    count = query.count()
    participants = query
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'count': count,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_provisional_list_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


def _process_delegation_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = DelegationsList._get_query(flag)
    participants = groupby(query, key=attrgetter('category'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_delegation_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_event_list(meeting_id, title, event_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = EventList._get_query(event_ids)
    count = query.count()
    participants = groupby(query, key=attrgetter('custom_field'))
    context = {'participants': participants,
               'count': count,
               'title': title,
               'template': 'meetings/printouts/_event_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_distribution(meeting_id, printout_type, title, flag):
    if printout_type == 'distribution':
        view_class = DocumentDistribution
    else:
        view_class = PigeonHoles
    g.meeting = Meeting.query.get(meeting_id)
    query = view_class._get_query(flag)
    participants = groupby(query, key=attrgetter('language'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'printout_type': view_class.printout_type,
               'table_class': view_class.table_class,
               'flag': flag,
               'template': 'meetings/printouts/_distribution_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_admission(meeting_id, flag, category_tags):
    g.meeting = Meeting.query.get(meeting_id)
    category_tags = (CategoryTag.query
                     .filter(CategoryTag.id.in_(category_tags))
                     .all())
    query = Admission._get_query(flag, category_tags)
    participants = query.all()
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    if not category_tags:
        title = 'General admission'
    else:
        title = (', '.join([tag.label for tag in category_tags])
                 + ' admission')
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'category_tags': category_tags,
               'template': 'meetings/printouts/_admission_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_credentials(meeting_id, title, flag, category_tags):
    g.meeting = Meeting.query.get(meeting_id)
    category_tags = (CategoryTag.query
                     .filter(CategoryTag.id.in_(category_tags))
                     .all())
    query = Credentials._get_query(flag, category_tags)
    participants = query.all()
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'category_tags': category_tags,
               'template': 'meetings/printouts/_credentials_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_media(meeting_id, title, flag, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = MediaList._get_query(flag, category_ids)
    participants = query.all()
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'category_ids': category_ids,
               'template': 'meetings/printouts/_media_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_verification(meeting_id, title, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = VerificationList._get_query(category_ids)
    count = query.count()
    participants = query
    context = {'participants': participants,
               'count': count,
               'title': title,
               'category_ids': category_ids,
               'template': 'meetings/printouts/_verification_table_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


def _process_parties(meeting_id, title, flag, category_tags, categories):
    g.meeting = Meeting.query.get(meeting_id)
    query = PartiesList._get_query(flag, category_tags, categories)
    participants = query.all()
    count = query.count()
    events = g.meeting.custom_fields.filter_by(field_type=CustomField.EVENT)
    context = {'participants': participants,
               'count': count,
               'events': events,
               'title': title,
               'template': 'meetings/printouts/_parties_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


def _process_observers(meeting_id, title, flag, category_tags, categories):
    g.meeting = Meeting.query.get(meeting_id)
    query = ObserversList._get_query(flag, category_tags, categories)
    participants = query.all()
    count = query.count()
    events = g.meeting.custom_fields.filter_by(field_type=CustomField.EVENT)
    context = {'participants': participants,
               'count': count,
               'events': events,
               'title': title,
               'template': 'meetings/printouts/_observers_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


class CategoriesForTags(MethodView):

    decorators = (login_required,)

    def get(self):
        category_tags = request.args.getlist('category_tags')
        categories = g.meeting.categories.order_by(Category.sort)
        if category_tags:
            categories = categories.filter(
                Category.tags.any(CategoryTag.id.in_(category_tags)))
        categories = [(c.id, c.title.english) for c in categories]
        return jsonify(categories)


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    JOB_NAME = 'participants excel'

    def post(self):
        _add_to_printout_queue(_process_participants_excel, self.JOB_NAME)
        return redirect(url_for('meetings.participants'))


def _process_participants_excel(meeting_id):
    g.meeting = Meeting.query.get(meeting_id)
    participants = get_participants_full(g.meeting.id)

    custom_fields = (
        g.meeting.custom_fields
        .filter_by(custom_field_type=CustomField.PARTICIPANT)
        .filter(CustomField.field_type.notin_((unicode(CustomField.IMAGE),
                                               unicode(CustomField.DOCUMENT))))
        .order_by(CustomField.sort))

    columns = [cf.slug for cf in custom_fields]
    header = [cf.label.english for cf in custom_fields]

    added_custom_fields = custom_fields.filter_by(is_primary=False)

    rows = []

    for p in participants:
        data = {}
        data['title'] = p.title.value
        data['first_name'] = p.first_name
        data['last_name'] = p.last_name
        data['badge_name'] = p.name_on_badge
        data['country'] = p.country.name if p.country else None
        data['email'] = p.email
        data['language'] = getattr(p.language, 'value', '-')
        data['category_id'] = p.category.title
        data['represented_country'] = (
            p.represented_country.name if p.represented_country else None)
        data['represented_region'] = (
            p.represented_region.value if p.represented_region else None)
        data['represented_organization'] = p.represented_organization
        data['attended'] = 'Yes' if p.attended else None
        data['verified'] = 'Yes' if p.verified else None
        data['credentials'] = 'Yes' if p.credentials else None

        for custom_field in added_custom_fields:
            if custom_field .field_type == CustomField.MULTI_CHECKBOX:
                custom_value = custom_field.custom_field_values.filter_by(participant=p).all()
            else:
                custom_value = custom_field.custom_field_values.filter_by(participant=p).first()

            if not custom_value:
                continue

            if custom_field.field_type == CustomField.COUNTRY:
                custom_value = Country(custom_value.value).name
            elif custom_field.field_type == CustomField.MULTI_CHECKBOX:
                custom_value = ', '.join([unicode(v.choice) for v in custom_value])
            else:
                custom_value = custom_value.value

            data[custom_field.slug] = custom_value

        rows.append([data.get(k) or '' for k in columns])

    filename = 'participants_{}.xls'.format(g.meeting.acronym)
    file_path = app.config['UPLOADED_PRINTOUTS_DEST'] / filename
    generate_excel(header, rows, str(file_path))
    return url_for('meetings.printouts_download', filename=filename)
