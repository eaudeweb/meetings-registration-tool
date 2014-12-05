from flask import Blueprint, g
from flask import current_app as app

from mrt.models import Meeting

from mrt.meetings import Meetings, MeetingEdit, RecipientsCount
from mrt.meetings import Registration, UserRegistration, UserRegistrationLogin
from mrt.meetings import UserRegistrationLogout, MediaRegistration

from mrt.meetings import Participants, ParticipantsFilter, ParticipantSearch
from mrt.meetings import ParticipantEdit, ParticipantDetail, ParticipantBadge
from mrt.meetings import DefaultParticipantDetail, DefaultParticipantEdit
from mrt.meetings import ParticipantRestore, ParticipantLabel
from mrt.meetings import ParticipantEnvelope, ParticipantsExport
from mrt.meetings import ParticipantAcknowledgeEmail, ParticipantAcknowledgePDF

from mrt.meetings import MediaParticipants, MediaParticipantsFilter
from mrt.meetings import MediaParticipantDetail, MediaParticipantEdit

from mrt.meetings import Categories, CategoryEdit, CategoryUpdatePosition
from mrt.meetings import PhraseEdit

from mrt.meetings import Notifications, NotificationEdit

from mrt.meetings import CustomFields, CustomFieldEdit, CustomFieldUpload
from mrt.meetings import CustomFieldRotate, CustomFieldCropUpload
from mrt.meetings import CustomFieldUpdatePosition

from mrt.meetings import Roles, RoleUserEdit
from mrt.meetings import BulkEmail, ActivityLogs
from mrt.meetings import Statistics, MailLogs, MailLogDetail, ResendEmail

from mrt.meetings import Badges, JobStatus, QueueStatus, PDFDownload
from mrt.meetings import ProcessingFileList
from mrt.meetings import ShortList, DelegationsList, PrintoutFooter


meetings = Blueprint('meetings', __name__, url_prefix='/meetings')


meetings.add_url_rule('', view_func=Meetings.as_view('home'))
meeting_edit_func = MeetingEdit.as_view('edit')
meetings.add_url_rule('/add', view_func=meeting_edit_func)
meetings.add_url_rule('/<int:meeting_id>/edit', view_func=meeting_edit_func)

# participant registration
meetings.add_url_rule('/<int:meeting_id>/registration',
                      view_func=Registration.as_view('registration'))
meetings.add_url_rule('/<int:meeting_id>/registration/user',
                      view_func=UserRegistration.as_view('registration_user'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/login',
    view_func=UserRegistrationLogin.as_view('registration_user_login'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/logout',
    view_func=UserRegistrationLogout.as_view('registration_user_logout'))

# media participant registration
meetings.add_url_rule(
    '/<int:meeting_id>/media_registration',
    view_func=MediaRegistration.as_view('media_registration'))

# participants
meetings.add_url_rule('/<int:meeting_id>/participants',
                      view_func=Participants.as_view('participants'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/filter',
    view_func=ParticipantsFilter.as_view('participants_filter'))
participant_edit_func = ParticipantEdit.as_view('participant_edit')
meetings.add_url_rule('/<int:meeting_id>/participants/add',
                      view_func=participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/edit',
    view_func=participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/detail',
    view_func=ParticipantDetail.as_view('participant_detail'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/badge',
    view_func=ParticipantBadge.as_view('participant_badge'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/label',
    view_func=ParticipantLabel.as_view('participant_label'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/envelope',
    view_func=ParticipantEnvelope.as_view('participant_envelope'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/acknowledge',
    view_func=ParticipantAcknowledgeEmail.as_view('participant_acknowledge'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/acknowledge/pdf',
    view_func=ParticipantAcknowledgePDF.as_view('participant_acknowledge_pdf'))

meetings.add_url_rule(
    '/<int:meeting_id>/participants/search',
    view_func=ParticipantSearch.as_view('participant_search'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/restore',
    view_func=ParticipantRestore.as_view('participant_restore'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/export',
    view_func=ParticipantsExport.as_view('participants_export'))

# default participants
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/<int:participant_id>/detail',
    view_func=DefaultParticipantDetail.as_view('default_participant_detail'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/<int:participant_id>/edit',
    view_func=DefaultParticipantEdit.as_view('default_participant_edit'))

# media participants
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants',
    view_func=MediaParticipants.as_view('media_participants'))
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/filter',
    view_func=MediaParticipantsFilter.as_view('media_participants_filter'))
media_participant_edit_func = MediaParticipantEdit.as_view(
    'media_participant_edit')
meetings.add_url_rule('/<int:meeting_id>/media_participants/add',
                      view_func=media_participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/<int:participant_id>/edit',
    view_func=media_participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/<int:participant_id>/detail',
    view_func=MediaParticipantDetail.as_view('media_participant_detail'))


# categories
meetings.add_url_rule('/<int:meeting_id>/settings/categories',
                      view_func=Categories.as_view('categories'))
category_edit_func = CategoryEdit.as_view('category_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/add',
    view_func=category_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/<int:category_id>/edit',
    view_func=category_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/update/position',
    view_func=CategoryUpdatePosition.as_view('category_update_position'))

# phrases
phrase_edit_func = PhraseEdit.as_view('phrase_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/phrases/<string:meeting_type>',
    view_func=phrase_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/phrases/<string:meeting_type>/<int:phrase_id>/edit',
    view_func=phrase_edit_func)

# custom fields
custom_field_edit_func = CustomFieldEdit.as_view('custom_field_edit')
meetings.add_url_rule('/<int:meeting_id>/settings/custom/fields',
                      view_func=CustomFields.as_view('custom_fields'))
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/add',
    view_func=custom_field_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/<int:custom_field_id>/edit',
    view_func=custom_field_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/update/position',
    view_func=CustomFieldUpdatePosition.as_view('custom_field_update_position'))

meetings.add_url_rule(
    '/<int:meeting_id>/participant/<int:participant_id>/custom/fields/<string:field_slug>/upload',
    view_func=CustomFieldUpload.as_view('custom_field_upload'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/custom/fields/<string:field_slug>/crop',
    view_func=CustomFieldCropUpload.as_view('custom_field_crop'))
meetings.add_url_rule(
    '/<int:meeting_id>/participant/<int:participant_id>/custom/fields/<string:field_slug>/rotate',
    view_func=CustomFieldRotate.as_view('custom_field_rotate'))

# printouts
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/processing',
    view_func=ProcessingFileList.as_view('processing_file_list'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/job/status',
    view_func=JobStatus.as_view('printouts_job_status'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/queue/<string:queue>/status',
    view_func=QueueStatus.as_view('printouts_queue_status'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/participant/badges',
    view_func=Badges.as_view('printouts_participant_badges'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/download/<string:filename>',
    view_func=PDFDownload.as_view('printouts_download'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/shortlist',
    view_func=ShortList.as_view('printouts_short_list'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/delegationlist',
    view_func=DelegationsList.as_view('printouts_delegation_list'))
meetings.add_url_rule(
    '/printouts/footer',
    view_func=PrintoutFooter.as_view('printouts_footer'))

# roles
meetings.add_url_rule('/<int:meeting_id>/settings/roles',
                      view_func=Roles.as_view('roles'))
role_user_edit_func = RoleUserEdit.as_view('role_user_edit')
meetings.add_url_rule('/<int:meeting_id>/settings/roles/add',
                      view_func=role_user_edit_func)
meetings.add_url_rule('/<int:meeting_id>/settings/roles/<int:role_user_id>',
                      view_func=role_user_edit_func)

# emails
meetings.add_url_rule('/<int:meeting_id>/email/bulk',
                      view_func=BulkEmail.as_view('bulkemail'))
meetings.add_url_rule('/<int:meeting_id>/email/recipients-count',
                      view_func=RecipientsCount.as_view('recipients_count'))


# logs
meetings.add_url_rule('/<int:meeting_id>/logs/statistics',
                      view_func=Statistics.as_view('statistics'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails',
                      view_func=MailLogs.as_view('mail_logs'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails/<int:mail_id>/detail',
                      view_func=MailLogDetail.as_view('mail_detail'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails/<int:mail_id>/resend',
                      view_func=ResendEmail.as_view('mail_resend'))
meetings.add_url_rule('/<int:meeting_id>/logs/activity',
                      view_func=ActivityLogs.as_view('activity'))

# notifications
meetings.add_url_rule('/<int:meeting_id>/settings/notifications',
                      view_func=Notifications.as_view('notifications'))
notification_edit = NotificationEdit.as_view('notification_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/notifications/add',
    view_func=notification_edit)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/notifications/<int:notification_id>/edit',
    view_func=notification_edit)


@meetings.url_defaults
def add_meeting_id(endpoint, values):
    meeting = getattr(g, 'meeting', None)
    if 'meeting_id' in values or not meeting:
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        values.setdefault('meeting_id', meeting.id)


@meetings.url_value_preprocessor
def add_meeting_global(endpoint, values):
    g.meeting = None
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        meeting_id = values.pop('meeting_id', None)
        if meeting_id:
            g.meeting = Meeting.query.get_or_404(meeting_id)
