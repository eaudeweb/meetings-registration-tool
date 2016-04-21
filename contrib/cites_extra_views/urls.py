
from .printouts import ObserversList
from flask import Blueprint
from mrt.common import add_meeting_id, add_meeting_global


blueprint = Blueprint('cites_extra_views', __name__, url_prefix='/meetings')

blueprint.add_url_rule(
    '/<int:meeting_id>/printouts/observers',
    view_func=ObserversList.as_view('printouts_observers'))

blueprint.url_defaults(add_meeting_id)
blueprint.url_value_preprocessor(add_meeting_global)
