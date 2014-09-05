from mrt.utils import get_translation
from babel import Locale


def test_get_translation_for_languages(app):
    aa_locale = Locale('aa')
    en_locale = Locale('en')
    fr_locale = Locale('fr')
    es_locale = Locale('es')

    with app.test_request_context():
        en_translation = get_translation(en_locale)
        aa_translation = get_translation(aa_locale)
        fr_translation = get_translation(fr_locale)
        es_translation = get_translation(es_locale)

    assert aa_translation
    assert en_translation
    assert es_translation
    assert fr_translation
    assert en_translation != fr_translation
    assert en_translation != es_translation
    assert fr_translation != es_translation
