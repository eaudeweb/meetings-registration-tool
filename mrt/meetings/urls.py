from flask import Blueprint
from mrt.meetings import MeetingAdd


meetings = Blueprint('meetings', __name__, url_prefix='/meetings')


meetings.add_url_rule('/add', view_func=MeetingAdd.as_view('add'))
