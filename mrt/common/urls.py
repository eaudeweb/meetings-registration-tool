"""
Helpers for meeting urls
"""
import mimetypes

from flask import Blueprint
from flask import Response
from flask import current_app as app
from flask import g
from flask.views import MethodView

from mrt.meetings.mixins import PermissionRequiredMixin


def add_meeting_id(endpoint, values):
    meeting = getattr(g, 'meeting', None)
    if 'meeting_id' in values or not meeting:
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        values.setdefault('meeting_id', meeting.id)
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_acronym'):
        values.setdefault('meeting_acronym', meeting.acronym)


def add_meeting_global(endpoint, values):
    from mrt.models import Meeting

    g.meeting = None
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        meeting_id = values.pop('meeting_id', None)
        if meeting_id:
            g.meeting = Meeting.query.get_or_404(meeting_id)
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_acronym'):
        acronym = values.pop('meeting_acronym', None)
        if acronym:
            g.meeting = Meeting.query.filter_by(acronym=acronym).first_or_404()


static_files = Blueprint('static_files', __name__, url_prefix="/static/files")


class ProtectedStaticFiles(PermissionRequiredMixin, MethodView):

    permission_required = (
        'manage_meeting',
        'manage_participant',
        'view_participant'
    )

    def get(self, url=""):
        file_path = app.config["FILES_PATH"] / url
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        # XXX This only works for nginx. If we switch to something else
        #  flask.send_file should be used.
        return Response(headers={
            "X-Accel-Redirect": "/protected_files/" + url,
            "Content-Type": content_type,
        })


static_files.add_url_rule("/<path:url>", view_func=ProtectedStaticFiles.as_view("protected_static_files"))