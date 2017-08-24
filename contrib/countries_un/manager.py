import click

import cPickle
import xlrd
import babel
from path import Path


@click.group()
def cli():
    pass

@cli.command(name='countries_un')
@click.pass_context
def update_countries_(ctx):
    app = ctx.obj['app']
    base_path = Path(app.instance_path).parent
    relative_path = 'mrt/static/localedata/countries_un.xlsx'
    workbook = xlrd.open_workbook("%s/%s" % (base_path, relative_path))
    sheet = workbook.sheet_by_index(0)
    country_codes = [str(cell.value) for cell in sheet.col(0)[1:]]
    template_name = babel.__path__[0] + '/localedata/%s.dat'
    for index, language in enumerate(['en', 'fr', 'es']):
        click.echo(u'Changed countries for language %s' % language)
        countries = [cell.value for cell in sheet.col(index + 1)[1:]]
        new_territories = dict(zip(country_codes, countries))

        path_to_file = template_name % language
        f = open(path_to_file, 'rb')
        locale_pickle = cPickle.load(f)
        f.close()

        locale_pickle['territories'] = new_territories
        f = open(path_to_file, 'w')
        cPickle.dump(locale_pickle, f)
        f.close()

    click.echo(u'A total of %d countries are now available for selection' %
               len(countries))
