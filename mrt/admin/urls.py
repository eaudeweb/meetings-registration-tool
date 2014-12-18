from flask import Blueprint

from mrt.admin import Categories, CategoryEdit, CategoryUpdatePosition
from mrt.admin import PhrasesTypes, PhraseEdit, Roles, RoleEdit
from mrt.admin import SettingsOverview, MeetingTypes, MeetingTypeEdit
from mrt.admin import StaffList, StaffEdit
from mrt.admin import Users, UserToggle, UserPasswordChange, UserDetail


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
admin.add_url_rule(
    '/categories/update/position',
    view_func=CategoryUpdatePosition.as_view('category_update_position'))

# Phrases
admin.add_url_rule('/phrases', view_func=PhrasesTypes.as_view('phrases'))
phrase_edit_func = PhraseEdit.as_view('phrase_edit')
admin.add_url_rule('/phrases/<string:meeting_type>',
                   view_func=phrase_edit_func)
admin.add_url_rule('/phrases/<string:meeting_type>/<int:phrase_id>',
                   view_func=phrase_edit_func)

# Roles
admin.add_url_rule('/roles', view_func=Roles.as_view('roles'))
role_edit_func = RoleEdit.as_view('role_edit')
admin.add_url_rule('/roles/add', view_func=role_edit_func)
admin.add_url_rule('/roles/<int:role_id>/edit', view_func=role_edit_func)

# Settings
admin.add_url_rule('/settings', view_func=SettingsOverview.as_view('settings'))

# Users
admin.add_url_rule('/users', view_func=Users.as_view('users'))
admin.add_url_rule(
    '/users/<int:user_id>/detail',
    view_func=UserDetail.as_view('user_detail'))
admin.add_url_rule('/users/<int:user_id>/toggle',
                   view_func=UserToggle.as_view('user_toggle'))
admin.add_url_rule('/users/<int:user_id>/edit',
                   view_func=UserPasswordChange.as_view('user_edit'))

# Meeting Types
admin.add_url_rule('/meeting-types',
                   view_func=MeetingTypes.as_view('meeting_types'))
meeting_type_func = MeetingTypeEdit.as_view('meeting_type_edit')
admin.add_url_rule('/meeting-types/add', view_func=meeting_type_func)
admin.add_url_rule('/meeting-types/<string:meeting_type_slug>/edit',
                   view_func=meeting_type_func)
