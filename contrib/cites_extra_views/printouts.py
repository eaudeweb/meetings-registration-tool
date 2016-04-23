
from flask import g, url_for, request, redirect, render_template
from flask.views import MethodView
from mrt.common.printouts import _add_to_printout_queue
from mrt.common.printouts import _PRINTOUT_MARGIN
from mrt.forms.meetings import FlagForm, CategoryTagForm
from mrt.forms.meetings import MediaCategoriesForm
from mrt.forms.meetings import ParticipantCategoriesForm
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.models import CustomField
from mrt.models import Participant, Category, CategoryTag, Meeting
from mrt.pdf import PdfRenderer
from sqlalchemy.orm import joinedload


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

        events = g.meeting.custom_fields.filter_by(
            field_type=CustomField.EVENT)

        query = self._get_query(flag, category_tags, categories)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items

        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        categories_form = ParticipantCategoriesForm(request.args)

        return render_template(
            'printouts/observers.html',
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
        args = (self.DOC_TITLE, flag, category_tags, categories)
        _add_to_printout_queue(_process_observers, self.JOB_NAME, *args)
        return redirect(url_for('.printouts_observers', flag=flag,
                                category_tags=category_tags,
                                categories=categories))


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
               'template': 'printouts/_observers_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


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

        events = g.meeting.custom_fields.filter_by(
            field_type=CustomField.EVENT)

        query = self._get_query(flag, category_tags, categories)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = pagination.items

        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        categories_form = ParticipantCategoriesForm(request.args)

        return render_template(
            'printouts/parties.html',
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
               'template': 'printouts/_parties_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


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
            'printouts/verification.html',
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


def _process_verification(meeting_id, title, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = VerificationList._get_query(category_ids)
    count = query.count()
    participants = query
    context = {'participants': participants,
               'count': count,
               'title': title,
               'category_ids': category_ids,
               'template': 'printouts/_verification_table_pdf.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


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
            choice for choice in flag_form.flag.choices
            if choice[0] != 'credentials']
        category_tags_form = CategoryTagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag_slug).first()

        return render_template(
            'printouts/credentials.html',
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
               'template': 'printouts/_credentials_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


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
            choice for choice in flag_form.flag.choices
            if choice[0] != 'credentials']
        categories_form = MediaCategoriesForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag_slug).first()

        return render_template(
            'printouts/media.html',
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


def _process_media(meeting_id, title, flag, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = MediaList._get_query(flag, category_ids)
    participants = query.all()
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'category_ids': category_ids,
               'template': 'printouts/_media_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()
