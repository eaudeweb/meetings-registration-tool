import pytest

from flask import Response
from flask import g

from mrt.pdf import stream_template
from .factories import MeetingFactory


def test_stream_template(app):
    path = app.config['TEMPLATES_PATH'] / 'template.html'
    output = 'Lorem ipsum dolor sit amet'
    with path.open('w+') as f:
        f.write(output)

    content = ''.join([chunk for chunk in stream_template('template.html')])
    assert content == output


def test_pdf_renderer_as_rq(app, pdf_renderer):
    renderer = pdf_renderer('template.html')

    with app.test_request_context():
        g.meeting = MeetingFactory()
        res = renderer.as_rq()
        assert isinstance(res, str)

    # Assert pdf file exists
    assert (app.config['UPLOADED_PRINTOUTS_DEST'] /
            renderer.pdf_path).exists()

    # Assert template deleted
    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()


def test_pdf_renderer_as_response(app, pdf_renderer):
    renderer = pdf_renderer('template.html')
    res = renderer.as_response()
    assert isinstance(res, Response)

    # Assert content is the same
    content = ''.join([chunk for chunk in res.response])
    assert pdf_renderer.content == content

    # Assert template and pdf file deleted
    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.pdf_path).exists()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()


def test_pdf_renderer_as_attachment(app, pdf_renderer):
    renderer = pdf_renderer('template.html')
    res = renderer.as_attachment()
    assert isinstance(res, file)

    # Assert content is the same
    assert pdf_renderer.content == res.read()

    # Assert template and pdf file deleted
    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.pdf_path).exists()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()


def test_pdf_renderer_deletes_on_error(app, pdf_renderer, monkeypatch):
    def _new_generate(self):
        with open(self.pdf_path, 'w') as f:
            f.write('dummy')
        raise Exception()

    monkeypatch.setattr(pdf_renderer, '_generate_pdf', _new_generate)
    renderer = pdf_renderer('template.html')

    with pytest.raises(Exception):
        renderer.as_attachment()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.pdf_path).exists()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()
