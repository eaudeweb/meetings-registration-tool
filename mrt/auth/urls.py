from flask import Blueprint
from mrt.auth import Login, Logout, RecoverPassword

auth = Blueprint('auth', __name__)

auth.add_url_rule('/login', view_func=Login.as_view('login'))
auth.add_url_rule('/logout', view_func=Logout.as_view('logout'))
auth.add_url_rule('/recover', view_func=RecoverPassword.as_view('recover'))
