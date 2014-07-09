from flask.ext.sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(35), nullable=False)
    last_name = db.Column(db.String(35), nullable=False)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(128))

    def __repr__(self):
        return '{} {}'.format(self.first_name, self.last_name)
