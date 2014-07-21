from flask import Blueprint
from mrt.admin import StaffList, StaffEdit
from mrt.admin import Categories


admin = Blueprint('admin', __name__, url_prefix='/admin')


admin.add_url_rule('/staff', view_func=StaffList.as_view('staff'))

staff_edit_func = StaffEdit.as_view('edit')

# Categories
admin.add_url_rule('/categories', view_func=Categories.as_view('categories'))
admin.add_url_rule('/staff/add', view_func=staff_edit_func)
admin.add_url_rule('/staff/<int:staff_id>/edit', view_func=staff_edit_func)
admin.add_url_rule('/staff/<int:staff_id>/delete', view_func=staff_edit_func)
