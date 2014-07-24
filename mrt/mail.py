from flask import current_app as app
from flask.ext.mail import Mail, Message


mail = Mail()


def send_reset_mail(email, token):
    url = app.config.get('HOSTNAME') + 'reset/' + token
    subject = "Reset your password"
    body = "Your reset link is: " + url
    sender = app.config.get('RESET_EMAIL')

    msg = Message(subject=subject, body=body, sender=sender,
                  recipients=[email, ])
    mail.send(msg)


def send_activation_mail(email, token):
    url = app.config.get('HOSTNAME') + 'reset/' + token
    subject = "Activate your account"
    body = "Your user has been created. To complete your activation \
follow the link: " + url
    sender = app.config.get('RESET_EMAIL')

    msg = Message(subject=subject, body=body, sender=sender,
                  recipients=[email, ])
    mail.send(msg)
