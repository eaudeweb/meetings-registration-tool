
CATEGORIES = (
    ('member', 'Member'),
    ('party', 'Party'),
    ('observer', 'Observer'),
    ('media', 'Media'),
    ('staff', 'Staff'),
    ('miscellaneous', 'Miscellaneous'),
)

COLORS = [
    ['#fff', '#0080FF', '#00BB22', '#FEF200', '#808080'],
    ['#faee38', '#f1c832', '#ff7dff', '#e7992c', '#de7426'],
    ['#d5181e', '#a81a21', '#93284c', '#69268e', '#492480'],
    ['#29487c', '#4071b7', '#7abff2', '#63e3ff', '#63afad'],
    ['#559751', '#c1d942', '#b0b7c0', '#c9a132', '#9b6633'],
]

MEETING_TYPES = (
    ('cop', 'Conference of the Parties'),
    ('ac', 'Animals Committee'),
    ('scc', 'Scientific Council'),
    ('sc', 'Standing Committee'),
    ('pc', 'Plants Committee'),
)

MEETING_SETTINGS = (
    ('media_participant_enabled', 'Enable Media Participants'),
)


CUSTOM_FIELDS = (
    ('text', 'Text'),
    ('image', 'Image'),
    ('checkbox', 'Checkbox'),
)


PERMISSIONS = (
    ('manage_user', 'Manage User'),
    ('manage_staff', 'Manage Staff'),
    ('manage_role', 'Manage Role'),
    ('manage_participant', 'Manage Participant'),
    ('view_participant', 'View Participant'),
    ('manage_media_participant', 'Manage Media Partipant'),
    ('view_media_participant', 'View Media Participant'),
    ('manage_meeting', 'Manage Meeting'),
    ('manage_category', 'Manage Category'),
    ('manage_phrases', 'Manage Phrases'),
    ('manage_default', 'Manage Default Values'),
)

ACTIVITY_ACTIONS = {
    'add': 'Add participant',
    'edit': 'Edit participant',
    'delete': 'Delete participant',
    'restore': 'Restore participant'
}

NOTIFICATION_TYPES = (
    ('notify_participant', 'Notify participant register'),
    ('notify_media_participant', 'Notify media participant register'),
)
