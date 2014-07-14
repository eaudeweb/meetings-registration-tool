from mrt.models import User, db


def test_model(app):
    user = User(email='johndoe@eaudeweb.ro')

    db.session.add(user)
    db.session.commit()

    count = User.query.count()
    assert count == 1


def test_view(app):
    with app.test_client() as client:
        response = client.get('/')

    assert response.status_code == 200
