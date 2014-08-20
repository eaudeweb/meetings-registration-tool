
from mrt.pdf import stream_template


def test_stream_template(app):
    path = app.config['TEMPLATES_PATH'] / 'template.html'
    output = 'Lorem ipsum dolor sit amet'
    with path.open('w+') as f:
        f.write(output)
    content = ''.join([chunk for chunk in stream_template(path.basename)])
    assert content == output
