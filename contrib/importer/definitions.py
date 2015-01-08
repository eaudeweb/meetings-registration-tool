
DEFAULT_COLOR = '#0080FF'
COLORS = {
    'blue stripe': '#0080FF',
    'green stripe': '#00BB22',
    'yellow stripe': '#FEF200',
    'grey stripe': '#808080',
    'bright yellow': '#faee38',
    'amber yellow': '#f1c832',
    'light pink': '#ff7dff',
    'sunset orange': '#e7992c',
    'burnt orange': '#de7426',
    'bright red': '#d5181e',
    'scarlet red': '#93284c',
    'bright purple': '#69268e',
    'dark purple': '#492480',
    'navy blue': '#29487c',
    'royal blue': '#4071b7',
    'sky blue': '#7abff2',
    'light blue': '#63e3ff',
    'sea green': '#63afad',
    'bottle green': '#559751',
    'lime green': '#c1d942',
    'silver': '#b0b7c0',
    'gold': '#c9a132',
    'bronze': '#9b6633',
}


REPRESENTING_TEMPLATES = {
    '${representing/country}': 'representing_country.html',
    '${representing/organization}': 'organization.html',
    '${representing/region} - ${representing/country}': 'region_country.html',
    '${representing/region/E} / '
    '${representing/region/S} / '
    '${representing/region/F} - '
    '${representing/country/E} / '
    '${representing/country/S} / '
    '${representing/country/F} ': 'region_country_translated.html',
    '${representing/region}': 'region.html',
    '${representing/region/E} / '
    '${representing/region/S} / '
    '${representing/region/F}  ': 'region.html',
    '${representing/country/E}': 'representing_country.html',
    '${representing/country/E} / '
    '${representing/country/S} / '
    '${representing/country/F}': 'representing_country_translated.html',
    '${personal/category}': 'category.html',
}
