import re
from datetime import datetime
import requests

ODATA_MEETINGS_URL = 'http://odata.cites.org/services/odata.svc/Meetings'
REPLACE_HOST = ('localhost:8081', 'odata.cites.org')


def fetch_entire_json(endpoint):
    limit = 50
    fetched = 0
    count = 0
    endpoint_format = endpoint + '?$format=json&$top={limit}'
    next_url = endpoint_format.format(limit=limit)
    entire_data = []
    while not fetched or fetched < count:
        result = requests.get(next_url)
        if result.status_code != 200:
            raise ValueError('Invalid return code %d' % result.status_code)
        data = result.json()
        entire_data.extend(data['d']['results'])
        count = int(data['d']['__count'])
        next_url = data['d']['__next']
        next_url = next_url.replace(*REPLACE_HOST)
        fetched += limit

    return entire_data


def get_date(text):
    datestr = re.findall("Date\((.*)\)", text)[0][:-3]
    return datetime.fromtimestamp(int(datestr))


def get_meetings():
    data = fetch_entire_json(ODATA_MEETINGS_URL)
    meetings = []
    for record in data:
        guid = (
            re.findall("Meetings\(\'(.*)\'\)", record['__metadata']['uri'])[0]
        )
        start = get_date(record['start'])
        end = get_date(record['end'])
        meetings.append({
            'guid': guid,
            'city': record['city'],
            'country': record['country'],
            'type': record['type'],
            'start': start, 'end': end,

        })
    return meetings
