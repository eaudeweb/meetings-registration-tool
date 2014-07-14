from meetings.models import User


def test_model(app, session):
    user = User(email='johndoe@eaudeweb.ro')

    session.add(user)
    session.commit()

    count = User.query.count()
    assert count == 1


def test_view(app):
    with app.test_client() as client:
        response = client.get('/')

    assert response.status_code == 200
