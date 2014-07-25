from flask.ext.assets import Environment, Bundle


_BUNDLE_CSS = (
    'css/bootstrap.min.css',
    'css/bootstrap-theme.min.css',
    'css/bootstrap-datetimepicker.min.css',
    'css/dataTables.bootstrap.css',
    'css/select2.css',
    'css/main.css',
)


_BUNDLE_JS = (
    'js/lib/jquery.min.js',
    'js/lib/bootstrap.min.js',
    'js/lib/moment.js',
    'js/lib/jquery.dataTables.min.js',
    'js/lib/dataTables.bootstrap.js',
    'js/lib/jquery.autosize.min.js',
    'js/lib/select2.min.js',
    'js/main.js',
)


_BUNDLE_DATEPICKER = (
    'js/lib/bootstrap-datetimepicker.min.js',
)


css = Bundle(*_BUNDLE_CSS, filters='cssmin', output='gen/static.css')
js = Bundle(*_BUNDLE_JS, filters='jsmin', output='gen/static.js')
datepicker = Bundle(*_BUNDLE_DATEPICKER,
                    output='gen/bootstrap-datetimepicker.min.js')


assets_env = Environment()
assets_env.register('css', css)
assets_env.register('js', js)
assets_env.register('datepicker', datepicker)
