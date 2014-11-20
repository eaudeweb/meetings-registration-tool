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

    # Assert template and pdf file deleted
    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.pdf_path).exists()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()


def test_pdf_renderer_as_attachement(app, pdf_renderer):
    renderer = pdf_renderer('template.html')
    res = renderer.as_attachement()
    assert isinstance(res, file)

    # Assert template and pdf file deleted
    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.pdf_path).exists()

    assert not (app.config['UPLOADED_PRINTOUTS_DEST'] /
                renderer.template_path).exists()
