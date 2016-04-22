from flask import Blueprint

from mrt.meetings import views
from mrt.common import add_meeting_id, add_meeting_global


meetings = Blueprint('meetings', __name__, url_prefix='/meetings')


meetings.add_url_rule('', view_func=views.Meetings.as_view('home'))
meeting_add_func = views.MeetingAdd.as_view('add')
meeting_edit_func = views.MeetingEdit.as_view('edit')
meeting_clone_func = views.MeetingClone.as_view('clone')
meetings.add_url_rule('/add', view_func=meeting_add_func)
meetings.add_url_rule('/<int:meeting_id>/edit', view_func=meeting_edit_func)
meetings.add_url_rule('/<int:meeting_id>/clone', view_func=meeting_clone_func)

#  registration
meetings.add_url_rule('/<string:meeting_acronym>/registration',
                      view_func=views.Registration.as_view('registration'))
meetings.add_url_rule(
    '/<string:meeting_acronym>/registration/media',
    view_func=views.MediaRegistration.as_view('media_registration'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/user',
    view_func=views.UserRegistration.as_view('registration_user'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/user/success',
    view_func=views.UserRegistrationSuccess.as_view(
        'registration_user_success'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/login',
    view_func=views.UserRegistrationLogin.as_view('registration_user_login'))
meetings.add_url_rule(
    '/<int:meeting_id>/registration/logout',
    view_func=views.UserRegistrationLogout.as_view('registration_user_logout'))

# participants
meetings.add_url_rule('/<int:meeting_id>/participants',
                      view_func=views.Participants.as_view('participants'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/filter',
    view_func=views.ParticipantsFilter.as_view('participants_filter'))
participant_edit_func = views.ParticipantEdit.as_view('participant_edit')
meetings.add_url_rule('/<int:meeting_id>/participants/add',
                      view_func=participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/edit',
    view_func=participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/detail',
    view_func=views.ParticipantDetail.as_view('participant_detail'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/badge',
    view_func=views.ParticipantBadge.as_view('participant_badge'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/label',
    view_func=views.ParticipantLabel.as_view('participant_label'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/envelope',
    view_func=views.ParticipantEnvelope.as_view('participant_envelope'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/acknowledge',
    view_func=views.ParticipantAcknowledgeEmail.as_view(
        'participant_acknowledge'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/acknowledge/pdf',
    view_func=views.ParticipantAcknowledgePDF.as_view(
        'participant_acknowledge_pdf'))

meetings.add_url_rule(
    '/<int:meeting_id>/participants/search',
    view_func=views.ParticipantSearch.as_view('participant_search'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/restore',
    view_func=views.ParticipantRestore.as_view('participant_restore'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/permanently/delete',
    view_func=views.ParticipantPermanentlyDelete.as_view(
        'participant_permanently_delete'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/export',
    view_func=views.ParticipantsExport.as_view('participants_export'))

# default participants
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/<int:participant_id>/detail',
    view_func=views.DefaultParticipantDetail.as_view(
        'default_participant_detail'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/media/<int:participant_id>/detail',
    view_func=views.DefaultMediaParticipantDetail.as_view(
        'default_media_participant_detail'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/<int:participant_id>/edit',
    view_func=views.DefaultParticipantEdit.as_view('default_participant_edit'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/media/<int:participant_id>/edit',
    view_func=views.DefaultMediaParticipantEdit.as_view(
        'default_media_participant_edit'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/search',
    view_func=views.DefaultParticipantSearch.as_view(
        'default_participant_search'))
meetings.add_url_rule(
    '/<int:meeting_id>/default_participant/media/search',
    view_func=views.DefaultMediaParticipantSearch.as_view(
        'default_media_participant_search'))

# media participants
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants',
    view_func=views.MediaParticipants.as_view('media_participants'))
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/filter',
    view_func=views.MediaParticipantsFilter.as_view(
        'media_participants_filter'))
media_participant_edit_func = views.MediaParticipantEdit.as_view(
    'media_participant_edit')
meetings.add_url_rule('/<int:meeting_id>/media_participants/add',
                      view_func=media_participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/<int:participant_id>/edit',
    view_func=media_participant_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/media_participants/<int:participant_id>/detail',
    view_func=views.MediaParticipantDetail.as_view('media_participant_detail'))


# categories
meetings.add_url_rule('/<int:meeting_id>/settings/categories',
                      view_func=views.Categories.as_view('categories'))
category_edit_func = views.CategoryEdit.as_view('category_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/add',
    view_func=category_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/<int:category_id>/edit',
    view_func=category_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/categories/update/position',
    view_func=views.CategoryUpdatePosition.as_view('category_update_position'))

# phrases
phrase_edit_func = views.PhraseEdit.as_view('phrase_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/phrases/<string:meeting_type>',
    view_func=phrase_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/phrases/<string:meeting_type>/'
    '<int:phrase_id>/edit',
    view_func=phrase_edit_func)

# custom fields
custom_field_edit_func = views.CustomFieldEdit.as_view('custom_field_edit')
meetings.add_url_rule('/<int:meeting_id>/settings/custom/fields',
                      view_func=views.CustomFields.as_view('custom_fields'))
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/<int:custom_field_id>/edit',
    view_func=custom_field_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/<string:custom_field_type>/add',
    view_func=custom_field_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/custom/fields/update/position',
    view_func=views.CustomFieldUpdatePosition.as_view(
        'custom_field_update_position'))

meetings.add_url_rule(
    '/<int:meeting_id>/participant/<int:participant_id>/custom/fields/'
    '<string:field_slug>/upload',
    view_func=views.CustomFieldUpload.as_view('custom_field_upload'))
meetings.add_url_rule(
    '/<int:meeting_id>/participants/<int:participant_id>/custom/fields/'
    '<string:field_slug>/crop',
    view_func=views.CustomFieldCropUpload.as_view('custom_field_crop'))
meetings.add_url_rule(
    '/<int:meeting_id>/participant/<int:participant_id>/custom/fields/'
    '<string:field_slug>/rotate',
    view_func=views.CustomFieldRotate.as_view('custom_field_rotate'))

# printouts
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/processing',
    view_func=views.ProcessingFileList.as_view('processing_file_list'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/job/status',
    view_func=views.JobStatus.as_view('printouts_job_status'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/queue/<string:queue>/status',
    view_func=views.QueueStatus.as_view('printouts_queue_status'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/participant/badges',
    view_func=views.Badges.as_view('printouts_participant_badges'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/download/<string:filename>',
    view_func=views.PDFDownload.as_view('printouts_download'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/shortlist',
    view_func=views.ShortList.as_view('printouts_short_list'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/delegationlist',
    view_func=views.DelegationsList.as_view('printouts_delegation_list'))
meetings.add_url_rule(
    '/printouts/footer',
    view_func=views.PrintoutFooter.as_view('printouts_footer'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/participant/events',
    view_func=views.EventList.as_view('printouts_participant_events'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/document_distribution',
    view_func=views.DocumentDistribution.as_view('printouts_document_distribution'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/provisionallist',
    view_func=views.ProvisionalList.as_view('printouts_provisional_list'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/admission',
    view_func=views.Admission.as_view('printouts_admission'))
meetings.add_url_rule(
    '/<int:meeting_id>/printouts/categories_for_tags',
    view_func=views.CategoriesForTags.as_view('categories_for_tags'))

# roles
meetings.add_url_rule('/<int:meeting_id>/settings/roles',
                      view_func=views.Roles.as_view('roles'))
role_user_edit_func = views.RoleUserEdit.as_view('role_user_edit')
meetings.add_url_rule('/<int:meeting_id>/settings/roles/add',
                      view_func=role_user_edit_func)
meetings.add_url_rule('/<int:meeting_id>/settings/roles/<int:role_user_id>',
                      view_func=role_user_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/roles/change/meeting/owner',
    view_func=views.RoleMeetingChangeOwner.as_view(
        'role_meeting_change_owner'))

# emails
meetings.add_url_rule('/<int:meeting_id>/email/bulk',
                      view_func=views.BulkEmail.as_view('bulkemail'))
meetings.add_url_rule(
    '/<int:meeting_id>/email/recipients',
    view_func=views.RecipientsBulkList.as_view('recipients'))
meetings.add_url_rule(
    '/<int:meeting_id>/email/recipients-count',
    view_func=views.RecipientsCount.as_view('recipients_count'))


# logs
meetings.add_url_rule('/<int:meeting_id>/settings/statistics',
                      view_func=views.Statistics.as_view('statistics'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails',
                      view_func=views.MailLogs.as_view('mail_logs'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails/<int:mail_id>/detail',
                      view_func=views.MailLogDetail.as_view('mail_detail'))
meetings.add_url_rule('/<int:meeting_id>/logs/mails/<int:mail_id>/resend',
                      view_func=views.ResendEmail.as_view('mail_resend'))
meetings.add_url_rule('/<int:meeting_id>/logs/activity',
                      view_func=views.ActivityLogs.as_view('activity'))

# notifications
meetings.add_url_rule('/<int:meeting_id>/settings/notifications',
                      view_func=views.Notifications.as_view('notifications'))
notification_edit = views.NotificationEdit.as_view('notification_edit')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/notifications/add',
    view_func=notification_edit)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/notifications/<int:notification_id>/edit',
    view_func=notification_edit)

# logos
meetings.add_url_rule('/<int:meeting_id>/logo/<string:logo_slug>/upload',
                      view_func=views.MeetingLogoUpload.as_view('logo_upload'))
meetings.add_url_rule('/<int:meeting_id>/settings/logos/',
                      view_func=views.Logos.as_view('logos'))

# rules
meetings.add_url_rule('/<int:meeting_id>/settings/rules/',
                      view_func=views.Rules.as_view('rules'))
rule_edit_func = views.RuleEdit.as_view('rule_edit')
meetings.add_url_rule('/<int:meeting_id>/settings/rules/'
                      '<any(participant, media):rule_type>/add',
                      view_func=rule_edit_func)
meetings.add_url_rule('/<int:meeting_id>/settings/rules/'
                     '<any(participant, media):rule_type>/<int:rule_id>/edit',
                      view_func=rule_edit_func)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/rules/<any(participant, media):rule_type>/data',
    view_func=views.RulesData.as_view('rules_data'))


# badge templates
badge_template = views.BadgeTemplates.as_view('badge_templates')
meetings.add_url_rule(
    '/<int:meeting_id>/settings/badge/templates',
    view_func=badge_template)
meetings.add_url_rule(
    '/<int:meeting_id>/settings/badge/templates/'
    '<any(default, default_shifted, standard, optimized, default_front_and_back):badge_template>',
    view_func=badge_template)

# manage duplicates
meetings.add_url_rule(
    '/<int:meeting_id>/duplicates/',
    view_func=views.ManageDuplicates.as_view('duplicates'))


meetings.url_defaults(add_meeting_id)
meetings.url_value_preprocessor(add_meeting_global)
