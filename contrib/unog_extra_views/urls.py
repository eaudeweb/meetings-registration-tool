from flask import Blueprint

from mrt.common import add_meeting_id, add_meeting_global

from .registration import Registration, MediaRegistration


blueprint = Blueprint('unog_extra_views', __name__,
                      template_folder='templates',
                      url_prefix='/')

blueprint.add_url_rule('<string:meeting_acronym>/registration',
                       view_func=Registration.as_view('registration'))
blueprint.add_url_rule(
    '<string:meeting_acronym>/registration/media',
    view_func=MediaRegistration.as_view('media_registration'))

blueprint.url_defaults(add_meeting_id)
blueprint.url_value_preprocessor(add_meeting_global)
