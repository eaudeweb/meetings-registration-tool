from flask import current_app as app, request, flash, g, url_for
from flask.ext.mail import Mail, Message

from datetime import datetime
from blinker import ANY

from mrt.models import db, Participant, MailLog, Phrase
from mrt.models import UserNotification
from mrt.signals import notification_signal, registration_signal


mail = Mail()


def get_default_sender():
    return app.config['DEFAULT_MAIL_SENDER']


def get_meeting_sender():
    if hasattr(g, 'meeting') and g.meeting and g.meeting.owner:
        return g.meeting.owner.user.email
    return get_default_sender()


def get_recipients(meeting, notification_type):
    recipients = (
        UserNotification.query.filter_by(
            meeting_id=meeting.id,
            notification_type=notification_type).all())
    if meeting.owner:
        recipients.append(meeting.owner)
    return recipients


def send_single_message(to, subject, message, sender=None, attachment=None,
                        attachment_name='attachment.pdf'):
    sender = sender or get_meeting_sender()
    if not sender:
        return False

    msg = Message(subject=subject, body=message, sender=sender,
                  recipients=[to])
    if attachment:
        msg.attach(attachment_name, "application/pdf", attachment.read())
    mail.send(msg)
    if g.get('meeting'):
        participant = (Participant.query.filter_by(email=to)
                       .participants().first())
        mail_log = MailLog(meeting=g.meeting, to=participant,
                           subject=subject, message=message,
                           date_sent=datetime.now())
        db.session.add(mail_log)
        db.session.commit()
    return True


def send_reset_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Reset your password"
    body = "Your reset link is: " + url

    send_single_message(email, subject=subject, message=body)


def send_activation_mail(email, token):
    url = request.url_root + 'reset/' + token
    subject = "Activate your account"
    body = ("Your user has been created. To complete your activation "
            "follow the link: " + url)

    send_single_message(email, subject=subject, message=body)


def send_bulk_message(recipients, subject, message):
    sent = 0
    s = get_meeting_sender()
    if not s:
        flash('No email for sender.', 'error')
        return sent

    for participant in recipients:
        email = participant.email
        if not email:
            flash('No email for {0}'.format(participant), 'error')
            continue
        send_single_message(email, subject=subject, message=message, sender=s)
        sent += 1
    return sent


@notification_signal.connect_via(ANY)
def send_notification_message(recipients, participant):
    sender = get_default_sender()
    if not sender:
        flash('No email for sender.', 'error')
        return
    if participant.participant_type.code == Participant.PARTICIPANT:
        model_class = 'Participant'
        url = url_for('meetings.participant_detail',
                      meeting_id=participant.meeting.id,
                      participant_id=participant.id)
        recipients = get_recipients(
            meeting=participant.meeting,
            notification_type='notify_participant')

    elif participant.participant_type.code == Participant.MEDIA:
        model_class = 'Media Participant'
        url = url_for('meetings.media_participant_detail',
                      meeting_id=participant.meeting.id,
                      participant_id=participant.id)
        recipients = get_recipients(
            meeting=participant.meeting,
            notification_type='notify_media_participant')

    else:
        flash('This model has no notification type set')
        return

    subject = "New %s has registered" % (model_class,)
    body = "A new %s has been registered %s" % (model_class,
                                                request.url_root + url)

    for recipient in recipients:
        msg = Message(subject=subject, body=body, sender=sender,
                      recipients=[recipient.user.email])
        mail.send(msg)


@registration_signal.connect_via(ANY)
def send_registration_message(sender, participant):
    sender = get_default_sender()
    if not sender:
        flash('No email for sender.', 'error')
        return
    subject = "%s registration confirmation" % (participant.meeting.acronym,)
    phrase = Phrase.query.filter_by(
        meeting=participant.meeting,
        group=Phrase.EMAIL_CONFIRMATION,
        name=Phrase.FOR_PARTICIPANTS).first()
    template = app.jinja_env.get_template(
        'meetings/registration/mail_template.html')
    body_html = template.render({'participant': participant,
                                 'phrase': phrase})

    msg = Message(subject=subject, html=body_html, sender=sender,
                  recipients=[participant.email])
    mail.send(msg)
