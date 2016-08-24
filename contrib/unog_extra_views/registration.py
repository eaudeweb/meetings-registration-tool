from mrt.meetings.registration import Registration as _Registration
from mrt.meetings.registration import MediaRegistration as _MediaRegistration


class Registration(_Registration):
    template_name = 'unog_registration/form.html'


class MediaRegistration(_MediaRegistration):
    template_name = 'unog_registration/form.html'
