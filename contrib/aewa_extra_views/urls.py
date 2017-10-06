
from .printouts import ProvisionalList, VerificationList
from flask import Blueprint
from mrt.common import add_meeting_id, add_meeting_global


blueprint = Blueprint('aewa_extra_views', __name__,
                      template_folder='templates',
                      url_prefix='/')

blueprint.add_url_rule(
    '<int:meeting_id>/printouts/provisionallist',
    view_func=ProvisionalList.as_view('printouts_provisional_list'))

blueprint.add_url_rule(
    '<int:meeting_id>/printouts/list_for_verification',
    view_func=VerificationList.as_view('printouts_verification'))


blueprint.url_defaults(add_meeting_id)
blueprint.url_value_preprocessor(add_meeting_global)
