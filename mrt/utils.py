import re
from PIL import Image
from unicodedata import normalize
from uuid import uuid4

from flask import current_app as app
from path import path


def unlink_participant_photo(filename):
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


def copy_model_fields(model, instance, exclude=[]):
    cls = model()
    for col in instance.__table__.columns:
        if col.name in exclude:
            continue
        setattr(cls, col.name, getattr(instance, col.name))
    return cls


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
