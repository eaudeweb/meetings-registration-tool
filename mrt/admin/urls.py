from flask import Blueprint
from mrt.admin import StaffList, StaffEdit


admin = Blueprint('admin', __name__, url_prefix='/admin')


admin.add_url_rule('/list', view_func=StaffList.as_view('list'))

staff_edit_func = StaffEdit.as_view('edit')
admin.add_url_rule('/add', view_func=staff_edit_func)
admin.add_url_rule('/<int:staff_id>/edit', view_func=staff_edit_func)
admin.add_url_rule('/<int:staff_id>/delete', view_func=staff_edit_func)
