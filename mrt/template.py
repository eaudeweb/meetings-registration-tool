import re
import time

from flask import current_app as app
from flask import request, g
from flask.ext.login import current_user

from babel import Locale
from babel.dates import format_date
from jinja2 import evalcontextfilter, Markup, escape
from path import path

from mrt.definitions import ACTIVITY_ACTIONS, PERMISSIONS_HIERARCHY
from mrt.utils import translate


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


def active(pattern):
    return 'active' if re.search(pattern, request.path) else ''


def countries(persons):
    countries = set()
    for person in persons:
        countries.add(person.country.name)
    return countries


def has_perm(permission, meeting=None):
    meeting = meeting or g.meeting
    return (current_user.is_superuser or
            current_user.staff is meeting.owner or
            current_user.has_perms(PERMISSIONS_HIERARCHY.get(permission, ()),
                                   meeting.id))


def date_processor(date_start, date_end, in_format='%Y-%m-%d',
                   out_format='d MMMM yyyy', locale='en_US'):

    if not date_end:
        return format_date(date_start, out_format, locale=locale)
    else:
        if date_start.year != date_end.year:
            # full dates for different years
            return '%s-%s' % (
                format_date(date_start, out_format, locale=locale),
                format_date(date_end, out_format, locale=locale))
        else:
            if date_start.month != date_end.month:
                # same years, different months
                return '%s-%s' % (
                    format_date(date_start, 'd MMMM', locale=locale),
                    format_date(date_end, out_format, locale=locale))
            else:
                if date_start.day != date_end.day:
                    # same year, same month, different days
                    return '%s-%s' % (
                        format_date(date_start, 'd', locale=locale),
                        format_date(date_end, out_format, locale=locale))
                else:
                    # same date
                    return format_date(date_start, out_format, locale=locale)


def crop(filename):
    file_path = path(app.config['UPLOADED_CROP_DEST']) / filename
    if file_path.exists() and file_path.isfile():
        return path(app.config['PATH_CROP_KEY']) / filename
    return filename


def no_image_cache(url):
    if app.config['TESTING']:
        return url
    return url + '?' + str(int(time.time()))


def activity_map(action):
    return ACTIVITY_ACTIONS.get(action, action)


def inject_static_file(filepath):
    data = None
    with open(path(app.static_folder) / filepath, 'r') as f:
        data = f.read()
    return Markup(data)


def country_in(country, lang_code='en'):
    return Locale(lang_code).territories.get(country.code)


def region_in(region, lang_code='en'):
    return translate(region.value, lang_code)


def pluralize(value, arg='s'):
    """
    Returns a plural suffix if the value is not 1. By default, 's' is used as
    the suffix:
    """

    if ',' not in arg:
        arg = ',' + arg
    bits = arg.split(',')
    if len(bits) > 2:
        return ''
    singular_suffix, plural_suffix = bits[:2]
    try:
        if float(value) != 1:
            return plural_suffix
    # Invalid string that's not a number.
    except ValueError:
        pass
    # Value isn't a string or a number; maybe it's a list?
    except TypeError:
        try:
            if len(value) != 1:
                return plural_suffix
        # len() of unsized object.
        except TypeError:
            pass
    return singular_suffix


def sort_by_tuple_element(value, position=0):
    def sort(item):
        value = item[position]
        if isinstance(value, basestring):
            return value.lower()
        return value
    return sorted(value, key=sort)


def convert_to_dict(value):
    try:
        return dict(value)
    except TypeError:
        return None
