import os
import subprocess
import uuid

from flask import current_app as app
from flask import Response, g, url_for

from mrt.utils import read_file


def stream_template(template_name, **context):
    app.update_template_context(context)
    template = app.jinja_env.get_template(template_name)
    rv = template.stream(context)
    rv.enable_buffering(5)
    return rv


def render_pdf(template_name, width=None, height=None,
               orientation="portrait", **context):
    template_path = (app.config['UPLOADED_PRINTOUTS_DEST'] /
                     (str(uuid.uuid4()) + '.html'))
    pdf_path = (app.config['UPLOADED_PRINTOUTS_DEST'] /
                (str(uuid.uuid4()) + '.pdf'))
    with open(template_path, 'w+') as f:
        for chunk in stream_template(template_name, **context):
            f.write(chunk.encode('utf-8'))

    def generate():
        command = ['wkhtmltopdf', '-q', '--encoding', 'utf-8',
                   '--page-height', height, '--page-width', width,
                   '--margin-bottom', '0', '--margin-top', '0',
                   '--margin-left', '0', '--margin-right', '0',
                   '--orientation', orientation,
                   str(template_path), str(pdf_path)]
        FNULL = open(os.devnull, 'w')
        subprocess.check_call(command, stdout=FNULL, stderr=subprocess.STDOUT)

    if g.get('is_rq_process'):
        generate()
        template_path.unlink_p()
        return url_for('meetings.printouts_download',
                       filename=str(pdf_path.name))

    try:
        generate()
        template_path.unlink_p()
        pdf = open(pdf_path, 'rb')
    finally:
        pdf_path.unlink_p()

    return Response(read_file(pdf), mimetype='application/pdf')


def _clean_printouts(results):
    count = 0
    for result in results:
        filename = result.split('/').pop()
        pdf_path = app.config['UPLOADED_PRINTOUTS_DEST'] / filename
        if pdf_path.exists():
            pdf_path.unlink_p()
            count += 1
    return count

