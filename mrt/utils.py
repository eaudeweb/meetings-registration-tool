from uuid import uuid4
from flask import current_app as app
from path import path


def unlink_uploaded_file(filename, config_key):
    if filename:
        path_from_config = path(
            app.config['UPLOADED_%s_DEST' % config_key.upper()])
        full_path = path_from_config / filename
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
