
from .printouts import ObserversList, PartiesList, VerificationList
from .printouts import Credentials, MediaList
from flask import Blueprint
from mrt.common import add_meeting_id, add_meeting_global


blueprint = Blueprint('cites_extra_views', __name__,
                      template_folder='templates',
                      url_prefix='/meetings')

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/observers',
    view_func=ObserversList.as_view('printouts_observers'))

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/parties',
    view_func=PartiesList.as_view('printouts_parties'))

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/list_for_verification',
    view_func=VerificationList.as_view('printouts_verification'))

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/credentials',
    view_func=Credentials.as_view('printouts_credentials'))

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/participant/media',
    view_func=MediaList.as_view('printouts_media'))

blueprint.url_defaults(add_meeting_id)
blueprint.url_value_preprocessor(add_meeting_global)


EXTRA_PRINTOUTS_MENU = (
    ('Print list of media participants',
     'cites_extra_views.printouts_media'),
    ('Print list of credentials',
     'cites_extra_views.printouts_credentials'),
    ('Print pigeon holes',
     'meetings.printouts_pigeon_holes'),
    ('Print list of participants for verification',
     'cites_extra_views.printouts_verification'),
    ('Print list of announced parties',
     'cites_extra_views.printouts_parties'),
    ('Print list of announced observers',
     'cites_extra_views.printouts_observers'),
)


@blueprint.app_context_processor
def inject_context():
    return {'EXTRA_PRINTOUTS_MENU': EXTRA_PRINTOUTS_MENU}
