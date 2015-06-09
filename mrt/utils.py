import operator
import os
import re
import xlwt

from datetime import date
from json import JSONEncoder as _JSONEncoder
from PIL import Image
from StringIO import StringIO
from unicodedata import normalize
from uuid import uuid4

from flask import _request_ctx_stack, current_app as app, g, url_for
from flask.ext.babel import refresh
from flask.ext.uploads import IMAGES, UploadSet

from raven.contrib.flask import Sentry
from sqlalchemy_utils import i18n
from werkzeug import FileStorage

from babel import support, Locale
from path import path


logos_upload = UploadSet('logos', IMAGES)


_LANGUAGES_MAP = {'english': 'en', 'french': 'fr', 'spanish': 'es'}
_LANGUAGES_ISO_MAP = {v: k for k, v in _LANGUAGES_MAP.items()}


sentry = Sentry()


class Logo(object):
    def __init__(self, slug):
        self.default_filename = app.config[slug.upper()]

    @property
    def meeting_name(self):
        return 'meeting_{}_{}'.format(g.meeting.id, self.default_filename)

    @property
    def filename(self):
        if hasattr(g, 'meeting'):
            meeting_logo_name = self.meeting_name
            if logos_upload.path(meeting_logo_name).exists():
                return meeting_logo_name
        return self.default_filename

    @property
    def path(self):
        return logos_upload.path(self.filename)

    @property
    def url(self):
        if g.get('is_pdf_process'):
            return self.path
        filename = '{}/{}'.format(app.config['PATH_LOGOS_KEY'], self.filename)
        return url_for('files', filename=filename)

    @property
    def default(self):
        return self.default_filename == self.filename

    def save(self, data):
        self.unlink()
        logos_upload.save(data, name=self.meeting_name)

    def unlink(self):
        unlink_uploaded_file(self.meeting_name, 'logos')
        unlink_thumbnail_file(self.meeting_name, dir_name='logos')


def unlink_participant_custom_file(filename):
    unlink_uploaded_file(filename, 'custom')
    unlink_uploaded_file(filename, 'crop',
                         dir_name=app.config['PATH_CUSTOM_KEY'])
    unlink_thumbnail_file(filename, dir_name='custom_uploads')
    unlink_thumbnail_file(filename, dir_name='crops')


def unlink_uploaded_file(filename, config_key, dir_name=None):
    if filename:
        dir_path = app.config['UPLOADED_%s_DEST' % config_key.upper()]
        if dir_name:
            dir_path = dir_path / dir_name
        full_path = dir_path / filename
        if full_path.isfile():
            full_path.unlink()


def unlink_thumbnail_file(filename, dir_name=None):
    if filename:
        name, ext = path(filename).splitext()
        thumb_path = app.config['UPLOADED_THUMBNAIL_DEST']
        if dir_name:
            thumb_path = thumb_path / dir_name
        if not thumb_path.exists():
            return
        for f in thumb_path.listdir():
            if f.basename().startswith(name):
                f.unlink()
        for dir_path in thumb_path.walkdirs():
            for f in dir_path.listdir():
                if f.basename().startswith(name):
                    f.unlink()


def duplicate_uploaded_file(filename, config_key):
    if filename:
        path_from_config = app.config['UPLOADED_%s_DEST' % config_key.upper()]
        full_path = path_from_config / filename
        if full_path.isfile():
            new_path = path_from_config / str(uuid4()) + full_path.ext
            full_path.copyfile(new_path)
            return new_path
    return False


def copy_attributes(destination, source, exclude_pk=True, exclude_fk=True,
                    exclude=[]):
    for col in destination.__table__.columns:
        if exclude_pk and col.primary_key:
            continue
        if exclude_fk and col.foreign_keys:
            continue
        if col.name in exclude:
            continue
        setattr(destination, col.name, getattr(source, col.name))
    return destination


_SLUG_RE = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _SLUG_RE.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def rotate_file(filename, config_key):
    """Rotates an image file, deletes the old one and returns the new filename
    """
    newfilename = str(uuid4()) + ".png"

    path_from_config = path(
        app.config['UPLOADED_%s_DEST' % config_key.upper()]
    )

    try:
        img = Image.open(path_from_config / filename)
        img = img.rotate(-90)
        img.save(path_from_config / newfilename, "PNG")
    except IOError:
        return filename

    unlink_uploaded_file(filename, config_key)
    return newfilename


def crop_file(filename, config_key, data):
    path_from_config = path(
        app.config['UPLOADED_%s_DEST' % config_key.upper()])
    img = Image.open(path_from_config / filename)
    img = img.crop(data)
    crop_path = (app.config['UPLOADED_CROP_DEST'] /
                 app.config['PATH_CUSTOM_KEY'])
    crop_path.makedirs_p()
    img.save(crop_path / filename)


def read_file(f):
    while True:
        data = f.read(131072)
        if data:
            yield data
        else:
            break
    f.close()


def generate_excel(header, rows):
    style = xlwt.XFStyle()
    normalfont = xlwt.Font()
    headerfont = xlwt.Font()
    headerfont.bold = True
    style.font = headerfont

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Sheet 1')
    row = 0

    for col in range(len(header)):
        ws.row(row).set_cell_text(col, header[col], style)

    style.font = normalfont

    for item in rows:
        row += 1
        for col in range(len(item)):
            ws.row(row).set_cell_text(col, unicode(item[col]), style)

    output = StringIO()
    wb.save(output)

    return output.getvalue()


def get_translation(locale):
    ctx = _request_ctx_stack.top
    if ctx is None:
        return None
    translations = getattr(ctx, 'translation_%s' % locale.language, None)
    if translations is None:
        dirname = os.path.join(ctx.app.root_path, 'translations')
        translations = support.Translations.load(dirname, [locale])
        setattr(ctx, 'translation_%s' % locale.language, translations)
    return translations


def translate(text, lang_code='en'):
    locale = Locale(lang_code)
    translations = get_translation(locale)
    if translations:
        return translations.gettext(text).decode('unicode-escape')
    return text


def set_language(lang='english'):
    if lang in ('english', 'french', 'spanish'):
        iso = _LANGUAGES_MAP.get(lang, 'en')
        g.language_verbose = lang
    if lang in ('en', 'fr', 'es'):
        iso = lang
        g.language_verbose = _LANGUAGES_ISO_MAP.get(lang, 'english')
    g.language = iso
    refresh()


def validate_email(email):
    """Email validation function used by create_user command"""
    if re.match("^[a-zA-Z0-9._%\-+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$", email):
        return True
    return False


def clean_email(emails):
    """Returns the first email from a string containing multiple emails"""
    for email in emails.split(','):
        email = email.strip()
        if validate_email(email):
            return email
    return None


def get_all_countries():
    territories = [
        (code, name)
        for code, name in i18n.get_locale().territories.items()
        if len(code) == 2 and code not in ('QO', 'QU', 'ZZ')
    ]
    return sorted(territories, key=operator.itemgetter(1))


def get_custom_file_as_filestorage(filename):
    file_path = app.config['UPLOADED_CUSTOM_DEST'] / filename
    try:
        data = FileStorage(stream=file_path.open(),
                           filename=file_path.basename())
    except IOError:
        data = None

    return data


class JSONEncoder(_JSONEncoder):

    def default(self, o):
        if isinstance(o, FileStorage):
            return str(o.filename)
        elif isinstance(o, date):
            return o.isoformat()
        return o


class CustomFieldLabel(object):

    def __init__(self, label):
        self.english = label.english
        self.french = label.french
        self.spanish = label.spanish

    def __unicode__(self):
        lang = getattr(g, 'language_verbose', 'english')
        return getattr(self, lang) or self.english
