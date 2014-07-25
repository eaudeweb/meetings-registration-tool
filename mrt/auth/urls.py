from flask import Blueprint
from mrt import auth as views

auth = Blueprint('auth', __name__)

auth.add_url_rule('/login', view_func=views.Login.as_view('login'))
auth.add_url_rule('/logout', view_func=views.Logout.as_view('logout'))
auth.add_url_rule('/recover',
                  view_func=views.RecoverPassword.as_view('recover'))
auth.add_url_rule('/reset/<string:token>',
                  view_func=views.ResetPassword.as_view('reset'))
auth.add_url_rule('/change-password',
                  view_func=views.ChangePassword.as_view('change_password'))
