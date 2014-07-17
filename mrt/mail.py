from flask.ext.mail import Mail, Message


mail = Mail()

def send_reset_mail(email, token):
    url = 'http://127.0.0.1:5000/reset/' + token
    mail_body = "Your reset link is: " + url
    sender = 'reset@eaudeweb.ro'

    msg = Message(mail_body, sender=sender, recipients=[email, ])
    mail.send(msg)
