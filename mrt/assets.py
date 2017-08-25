from flask_assets import Environment, Bundle


_BUNDLE_CSS = (
    'css/bootstrap.min.css',
    'css/bootstrap-theme.min.css',
    'css/bootstrap-datetimepicker.min.css',
    'css/dataTables.bootstrap.css',
    'css/fancybox/jquery.fancybox.css',
    'css/select2.min.css',
    'css/main.css',
)


_BUNDLE_JS = (
    'js/lib/jquery.min.js',
    'js/lib/jquery-ui.min.js',
    'js/lib/bootstrap.min.js',
    'js/lib/moment.js',
    'js/lib/jquery.dataTables.min.js',
    'js/lib/dataTables.bootstrap.js',
    'js/lib/jquery.autosize.min.js',
    'js/lib/select2.min.js',
    'js/lib/jquery.fancybox.js',
    'js/lib/jquery.sortable.js',
    'js/lib/jquery.typeahead.js',
    'js/lib/jquery.ba-dotimeout.js',
    'js/lib/jquery.infinitescroll.min.js',
    'js/lib/jquery.chained.remote.min.js',
    'js/lib/bootstrap-datetimepicker.min.js',
    'js/main.js',
    'js/printouts.js',
    'js/rule.js',
)


_BUNDLE_COLORPICKER_JS = (
    'js/lib/spectrum.js',
)
_BUNDLE_COLORPICKER_CSS = (
    'css/spectrum.css',
)


_BUNDLE_SHOWIF = (
    'js/lib/jquery.min.js',
    'js/lib/jquery.showif.js',
)


_BUNDLE_UPLOAD_JS = (
    'js/lib/jquery_file_upload/jquery.ui.widget.js',
    'js/lib/jquery_file_upload/jquery.iframe-transport.js',
    'js/lib/jquery_file_upload/jquery.fileupload.js',
    'js/lib/jquery.Jcrop.js'
)

_BUNDLE_UPLOAD_CSS = (
    'css/jcrop/jquery.Jcrop.css',
)


_BUNDLE_REGISTRATION_CSS = (
    'css/bootstrap.min.css',
    'css/bootstrap-theme.min.css',
    'css/bootstrap-datetimepicker.min.css',
    'css/registration.css',
)
_BUNDLE_REGISTRATION_JS = (
    'js/lib/jquery.min.js',
    'js/lib/jquery.showif.js',
    'js/file_validation.js',
    'js/lib/moment.js',
    'js/lib/bootstrap-datetimepicker.min.js',
)

_BUNDLE_ERROR_CSS = (
    'css/bootstrap.min.css',
    'css/error.css',
)

css = Bundle(*_BUNDLE_CSS, filters='cssmin', output='gen/static.css')
js = Bundle(*_BUNDLE_JS, filters='jsmin', output='gen/static.js')
showif = Bundle(*_BUNDLE_SHOWIF, output='gen/showif.js')
upload_js = Bundle(*_BUNDLE_UPLOAD_JS, output='gen/jquery.file.upload.min.js')
upload_css = Bundle(*_BUNDLE_UPLOAD_CSS,
                    output='gen/jquery.file.upload.min.css')
colorpicker_js = Bundle(*_BUNDLE_COLORPICKER_JS,
                        output='gen/spectrum.min.js')
colorpicker_css = Bundle(*_BUNDLE_COLORPICKER_CSS,
                         output='gen/spectrum.min.css')
registration_css = Bundle(*_BUNDLE_REGISTRATION_CSS,
                          output='gen/registration.min.css')
registration_js = Bundle(*_BUNDLE_REGISTRATION_JS,
                         output='gen/registration.min.js')
error_css = Bundle(*_BUNDLE_REGISTRATION_CSS,
                   output='gen/error.min.css')

assets_env = Environment()
assets_env.register('css', css)
assets_env.register('js', js)
assets_env.register('showif', showif)
assets_env.register('upload_js', upload_js)
assets_env.register('upload_css', upload_css)

assets_env.register('colorpicker_js', colorpicker_js)
assets_env.register('colorpicker_css', colorpicker_css)

assets_env.register('registration_css', registration_css)
assets_env.register('registration_js', registration_js)

assets_env.register('error_css', error_css)
