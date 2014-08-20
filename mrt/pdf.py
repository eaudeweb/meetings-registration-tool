import tempfile
import uuid

from flask import current_app as app
from flask import Response
from path import path


def stream_template(template_name, **context):
    app.update_template_context(context)
    template = app.jinja_env.get_template(template_name)
    rv = template.stream(context)
    rv.enable_buffering(5)
    return rv


def render_as_pdf(template_name, **context):
    template_path = path(tempfile.mkdtemp()) / uuid.uuid4()
    with open(template_path, 'w+') as f:
        for chunk in stream_template(template_name, **context):
            f.write(chunk.encode('utf-8'))
    return Response()
