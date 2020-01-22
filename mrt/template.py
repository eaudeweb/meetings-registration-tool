import re
import time
from bleach import clean

from flask import url_for
from flask import current_app as app
from flask import request, g
from flask_login import current_user

from babel.dates import format_date
from jinja2 import evalcontextfilter, Markup
from path import Path

from mrt.definitions import ACTIVITY_ACTIONS, PERMISSIONS_HIERARCHY
from mrt.utils import translate, Logo


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                          for p in _paragraph_re.split(value or ''))
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
            return '%s - %s' % (
                format_date(date_start, out_format, locale=locale),
                format_date(date_end, out_format, locale=locale))
        else:
            if date_start.month != date_end.month:
                # same years, different months
                return '%s - %s' % (
                    format_date(date_start, out_format.replace(' yyyy', ''),
                                locale=locale),
                    format_date(date_end, out_format, locale=locale))
            else:
                if date_start.day != date_end.day:
                    # same year, same month, different days
                    return '%s - %s' % (
                        format_date(date_start, 'd', locale=locale),
                        format_date(date_end, out_format, locale=locale))
                else:
                    # same date
                    return format_date(date_start, out_format, locale=locale)


def year_processor(date_start, date_end, in_format='%Y-%m-%d',
                   out_format='yyyy', locale='en_US'):
    if not date_end:
        return format_date(date_start, out_format, locale=locale)
    else:
        if date_start.year != date_end.year:
            return '%s - %s' % (
                format_date(date_start, out_format, locale=locale),
                format_date(date_end, out_format, locale=locale))
        else:
            return format_date(date_start, out_format, locale=locale)


def crop(filename):
    file_path = Path(app.config['UPLOADED_CROP_DEST']) / filename
    if file_path.exists() and file_path.isfile():
        return Path(app.config['PATH_CROP_KEY']) / filename
    return filename


def no_image_cache(url):
    if app.config['TESTING']:
        return url
    return url + '?' + str(int(time.time())) if url else ''


def activity_map(action):
    return ACTIVITY_ACTIONS.get(action, action)


def inject_static_file(filepath):
    data = None
    with open(Path(app.static_folder) / filepath, 'r') as f:
        data = f.read()
    return Markup(data)


def inject_badge_context(participant):
    product_logo = Logo('product_logo')
    product_side_logo = Logo('product_side_logo')
    badge_back_logo = Logo('badge_back_logo')

    participant_photo, background, = None, None
    if participant.photo:
        crop_photo = crop(Path(app.config['PATH_CUSTOM_KEY']) /
                          participant.photo)
        participant_photo = app.config['FILES_PATH'] / crop_photo

    if participant.category.background:
        background = (app.config['UPLOADED_BACKGROUNDS_DEST'] /
                      participant.category.background)
    return {
        'product_logo': product_logo,
        'product_side_logo': product_side_logo,
        'badge_back_logo': badge_back_logo,
        'participant_photo': participant_photo,
        'background': background,
    }


def region_in(region, lang_code='en'):
    if not region:
        return ''
    if isinstance(region, basestring):
        return translate(region, lang_code)
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


def clean_html(text, **kwargs):
    return Markup(clean(unicode(text).encode('utf-8'), **kwargs))


def url_external(view_name, **kwargs):
    if app.config.get('DOMAIN_NAME', None):
        return app.config['DOMAIN_NAME'] + url_for(view_name, **kwargs)
    return url_for(view_name, _external=True, **kwargs)
