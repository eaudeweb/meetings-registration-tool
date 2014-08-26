from flask import g
from flask import request, render_template
from flask.views import MethodView

from mrt.models import Participant, Category


class Badges(MethodView):

    def get(self):
        category_ids = request.args.get('categories')
        page = request.args.get('page', 1, type=int)
        participants = Participant.query.filter_by(meeting=g.meeting)
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        participants = participants.paginate(page, per_page=50)
        return render_template('meetings/printouts/badges.html',
                               participants=participants,
                               category_ids=category_ids)
