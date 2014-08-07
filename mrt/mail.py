from flask import current_app as app, request, flash
from flask.ext.mail import Mail, Message


mail = Mail()


def send_reset_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Reset your password"
    body = "Your reset link is: " + url
    sender = app.config['DEFAULT_MAIL_SENDER']
    msg = Message(subject=subject, body=body, sender=sender,
                  recipients=[email, ])
    mail.send(msg)


def send_activation_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Activate your account"
    body = ("Your user has been created. To complete your activation "
            "follow the link: " + url)
    sender = app.config['DEFAULT_MAIL_SENDER']

    msg = Message(subject=subject, body=body, sender=sender,
                  recipients=[email, ])
    mail.send(msg)


def send_bulk_message(recipients, subject, message):
    sender = app.config['DEFAULT_MAIL_SENDER']

    sent = 0
    for participant in recipients:
        email = participant.email
        if not email:
            flash('No email for {0}'.format(participant), 'error')
            continue
        msg = Message(subject=subject, body=message, sender=sender,
                      recipients=[email])
        mail.send(msg)
        sent += 1
    return sent
