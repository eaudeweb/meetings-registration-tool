
from flask import g, url_for, request, redirect, render_template
from flask.views import MethodView
from mrt.forms.meetings import FlagForm, CategoryTagForm
from mrt.forms.meetings import ParticipantCategoriesForm
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.meetings.printouts_common import _add_to_printout_queue
from mrt.meetings.printouts_common import _PRINTOUT_MARGIN
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
