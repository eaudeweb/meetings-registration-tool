import operator

import six
from babel import Locale
from sqlalchemy import types

from sqlalchemy_utils import i18n
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible
from wtforms_components import SelectField


_KOREAN_OFFICIAL_NAMES = {
    'en': u'Democratic People\u2019s Republic of Korea',
    'es': u'Rep\u00FAblica Popular Democr\u00E1tica de Corea',
    'fr': u' R\u00E9publique populaire d\u00E9mocratique de Cor\u00E9e'
}


def get_all_countries():
    territories = [
        (code, name)
        for code, name in six.iteritems(i18n.get_locale().territories)
        if len(code) == 2 and code not in ('QO', 'QU', 'ZZ', 'KP')
    ]
    territories.append(
        (
            'KP', _KOREAN_OFFICIAL_NAMES[i18n.get_locale().language]
        )
    )
    return sorted(territories, key=operator.itemgetter(1))


def country_in(country, lang_code='en'):
    if not country:
        return ''
    if country.code == 'KP':
        return _KOREAN_OFFICIAL_NAMES[lang_code]
    return Locale(lang_code).territories.get(country.code)


class Country(object):
    def __init__(self, code_or_country):
        if isinstance(code_or_country, Country):
            self.code = code_or_country.code
        else:
            self.code = code_or_country

    @property
    def name(self):
        for code, name in get_all_countries():
            if code == self.code:
                return name
        return ''

    def __eq__(self, other):
        if isinstance(other, Country):
            return self.code == other.code
        elif isinstance(other, six.string_types):
            return self.code == other
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.code)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class CountryType(types.TypeDecorator, ScalarCoercible):
    impl = types.String(2)
    python_type = Country

    def process_bind_param(self, value, dialect):
        if isinstance(value, Country):
            return value.code

        if isinstance(value, six.string_types):
            return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return Country(value)

    def _coerce(self, value):
        if value is not None and not isinstance(value, Country):
            return Country(value)
        return value


class CountryField(SelectField):
    def __init__(self, *args, **kwargs):
        kwargs['coerce'] = Country
        super(CountryField, self).__init__(*args, **kwargs)
        self.choices = self._get_choices

    def _get_choices(self):
        return get_all_countries()
