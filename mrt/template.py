import re

from babel.dates import format_date
from flask import request
from jinja2 import evalcontextfilter, Markup, escape


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
