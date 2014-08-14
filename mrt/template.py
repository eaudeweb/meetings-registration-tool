import re
import time

from flask import current_app as app
from flask import request
from path import path
from jinja2 import evalcontextfilter, Markup, escape
from babel.dates import format_date

from mrt.definitions import ACTIVITY_ACTIONS


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
