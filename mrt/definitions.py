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
    ('hide_login_button', 'Hide Login button on registration form'),
)


PERMISSIONS = (
    ('manage_participant', 'Manage Participant'),
    ('view_participant', 'View Participant'),
    ('manage_media_participant', 'Manage Media Participant'),
    ('view_media_participant', 'View Media Participant'),
    ('manage_meeting', 'Manage Meeting'),
)

PERMISSIONS_HIERARCHY = {
    'manage_meeting': ('manage_meeting', ),
    'manage_participant': ('manage_meeting', 'manage_participant'),
    'view_participant': ('manage_meeting', 'manage_participant',
                         'view_participant'),
    'manage_media_participant': ('manage_meeting', 'manage_media_participant'),
    'view_media_participant': ('manage_meeting', 'manage_media_participant',
                               'view_media_participant'),
}


ACTIVITY_ACTIONS = {
    'add': 'Add participant',
    'edit': 'Edit participant',
    'delete': 'Delete participant',
    'restore': 'Restore participant'
}


NOTIFY_PARTICIPANT = (
    'notify_participant', 'Notify when participant registers')
NOTIFY_MEDIA_PARTICIPANT = (
    'notify_media_participant', 'Notify when media participant registers')

NOTIFICATION_TYPES = (NOTIFY_PARTICIPANT, NOTIFY_MEDIA_PARTICIPANT)


PRINTOUT_TYPES = (
    ('announced', 'Announced'),
    ('attending', 'Attending'),
)


REPRESENTING_REGIONS = (
    ('Africa', 'Africa'),
    ('Asia', 'Asia'),
    ('Central and South America and the Carribean',
     'Central and South America and the Carribean'),
    ('Depositary Government', 'Depositary Government'),
    ('Europe', 'Europe'),
    ('Next host country', 'Next host country'),
    ('North America', 'North America'),
    ('Oceania', 'Oceania'),
    ('Previous host country', 'Previous host country')
)


CATEGORY_REPRESENTING = (
    ('organization.html', 'Organization'),
    ('region_country.html', 'Region - Country'),
    ('region_country_translated.html',
        'Region E / Region S / Region F - Country E / Country S / Country F'),
    ('region_translated.html', 'Region E / Region S / Region F'),
    ('region.html', 'Region'),
    ('representing_country.html', 'Representing country'),
    ('representing_country_translated.html',
     'Representing country E / Representing country S / '
     'Representing country F'),
    ('category.html', 'Category'),
)


BADGE_W = '3.4in'
BADGE_H = '2.15in'
BADGE_A6_W = '5.8in'
BADGE_A6_H = '4.1in'
LABEL_W = '11.7in'
LABEL_H = '8.3in'
ENVEL_W = '9.0in'
ENVEL_H = '6.4in'
ACK_W = '8.26in'
ACK_H = '11.7in'


LANGUAGES_MAP = {'english': 'en', 'french': 'fr', 'spanish': 'es'}
LANGUAGES_ISO_MAP = {v: k for k, v in LANGUAGES_MAP.items()}
