from flask import current_app as app, request, flash, g
from flask.ext.mail import Mail, Message


mail = Mail()


def get_default_sender():
    if g.meeting.owner:
        return g.meeting.owner.user.email
    return app.config['DEFAULT_MAIL_SENDER']


def send_single_message(to, subject, message, sender=None):
    sender = sender or get_default_sender()
    msg = Message(subject=subject, body=message, sender=sender,
                  recipients=[to])
    mail.send(msg)


def send_reset_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Reset your password"
    body = "Your reset link is: " + url
    sender = app.config['DEFAULT_MAIL_SENDER']

    send_single_message(email, subject=subject, message=body, sender=sender)


def send_activation_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Activate your account"
    body = ("Your user has been created. To complete your activation "
            "follow the link: " + url)
    sender = app.config['DEFAULT_MAIL_SENDER']

    send_single_message(email, subject=subject, message=body, sender=sender)


def send_bulk_message(recipients, subject, message):
    sent = 0
    sender = get_default_sender()

    if not sender:
        flash('No email for sender.', 'error')
        return sent

    for participant in recipients:
        email = participant.email
        if not email:
            flash('No email for {0}'.format(participant), 'error')
            continue
        send_single_message(email, subject=subject, message=message,
                            sender=sender)
        sent += 1
    return sent
