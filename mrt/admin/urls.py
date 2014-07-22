from flask import Blueprint
from mrt.admin import StaffList, StaffEdit
from mrt.admin import Categories, CategoryEdit


admin = Blueprint('admin', __name__, url_prefix='/admin')


admin.add_url_rule('/staff', view_func=StaffList.as_view('staff'))

# Staff
staff_edit_func = StaffEdit.as_view('staff_edit')
admin.add_url_rule('/staff/add', view_func=staff_edit_func)
admin.add_url_rule('/staff/<int:staff_id>/edit', view_func=staff_edit_func)

# Categories
admin.add_url_rule('/categories', view_func=Categories.as_view('categories'))
category_edit_func = CategoryEdit.as_view('category_edit')
admin.add_url_rule('/categories/add', view_func=category_edit_func)
admin.add_url_rule('/categories/<int:category_id>/edit',
                   view_func=category_edit_func)
