import os
import subprocess
import uuid

from flask import current_app as app
from flask import Response, g, url_for
from mrt.template import url_external

from mrt.utils import read_file


_PAGE_DEFAULT_MARGIN = {'top': '0', 'bottom': '0', 'left': '0', 'right': '0'}


def stream_template(template_name, **context):
    app.update_template_context(context)
    template = app.jinja_env.get_template(template_name)
    rv = template.stream(context)
    rv.enable_buffering(5)
    return rv


class PdfRenderer(object):
    def __init__(self, template_name, **kwargs):
        self.template_name = template_name
        self.title = kwargs.get('title', '')
        self.width = kwargs.get('width', None)
        self.height = kwargs.get('height', None)
        self.margin = kwargs.get('margin', _PAGE_DEFAULT_MARGIN)
        self.orientation = kwargs.get('orientation', 'portrait')
        self.footer = kwargs.get('footer', True)
        self.context = kwargs.get('context', {})

        self.template_path = (app.config['UPLOADED_PRINTOUTS_DEST'] /
                              (str(uuid.uuid4()) + '.html'))
        self.pdf_path = (app.config['UPLOADED_PRINTOUTS_DEST'] /
                         (str(uuid.uuid4()) + '.pdf'))
        g.is_pdf_process = True

    def _render_template(self):
        with open(self.template_path, 'w+') as f:
            for chunk in stream_template(self.template_name, **self.context):
                f.write(chunk.encode('utf-8'))

    def _generate_pdf(self):
        command = ['wkhtmltopdf', '-q',
                   '--encoding', 'utf-8',
                   '--page-height', self.height,
                   '--page-width', self.width,
                   '-B', self.margin['bottom'],
                   '-T', self.margin['top'],
                   '-L', self.margin['left'],
                   '-R', self.margin['right'],
                   '--orientation', self.orientation]
        if self.title:
            command += ['--title', self.title]

        if self.footer and not app.config['DEBUG']:
            footer_url = url_external('meetings.printouts_footer')
            command += ['--footer-html', footer_url]
        command += [str(self.template_path), str(self.pdf_path)]

        FNULL = open(os.devnull, 'w')
        subprocess.check_call(command, stdout=FNULL, stderr=subprocess.STDOUT)

    def _generate(self):
        self._render_template()
        try:
            self._generate_pdf()
        finally:
            self.template_path.unlink_p()

    def as_rq(self):
        self._generate()
        return url_for('meetings.printouts_download',
                       filename=str(self.pdf_path.name))

    def as_attachment(self):
        return self._pdf_file()

    def as_response(self):
        return Response(read_file(self._pdf_file()), mimetype='application/pdf')

    def _pdf_file(self):
        try:
            self._generate()
            pdf = open(self.pdf_path, 'rb')
        finally:
            self.pdf_path.unlink_p()
        return pdf


def _clean_printouts(results):
    count = 0
    for result in results:
        filename = result.split('/').pop()
        pdf_path = app.config['UPLOADED_PRINTOUTS_DEST'] / filename
        if pdf_path.exists():
            pdf_path.unlink_p()
            count += 1
    return count
