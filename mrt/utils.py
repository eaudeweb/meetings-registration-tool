import os
import re
from flask import current_app as app
from path import path
from unicodedata import normalize
from uuid import uuid4
from PIL import Image


def unlink_uploaded_file(filename, config_key):
    if filename:
        path_from_config = path(
            app.config['UPLOADED_%s_DEST' % config_key.upper()])
        full_path = path_from_config / filename
        if full_path.isfile():
            full_path.unlink()
            return True
    return False


def unlink_thumbnail_file(filename, config_key):
    if filename:
        name, ext = os.path.splitext(filename)
        pattern = '^%s_(\d+)x(\d+)_(\d+).png' % (name,)
        path_from_config = path(
            app.config['UPLOADED_%s_DEST' % config_key.upper()])
        for f in os.listdir(path_from_config):
            if re.search(pattern, f):
                full_path = path_from_config / f
                if full_path.isfile():
                    full_path.unlink()
        return True
    return False


def duplicate_uploaded_file(filename, config_key):
    if filename:
        path_from_config = path(
            app.config['UPLOADED_%s_DEST' % config_key.upper()])
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
