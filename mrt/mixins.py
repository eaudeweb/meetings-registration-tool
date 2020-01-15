
from flask import request, jsonify, abort, Response
from flask import current_app as app
from flask_login import current_user as user
from querystring_parser import parser


class FilterView(object):

    def get(self):
        args = parser.parse(request.query_string)
        options = {
            'start': args.get('start', 0),
            'limit': args.get('length', 10),
            'search': args.get('search', {}).get('value'),
        }

        columns = []
        for i in range(len(args['columns'])):
            columns.append(args['columns'][i])

        order = []
        for i in range(len(args['order'])):
            column_id = args['order'][i]['column']
            order.append({
                'column': columns[column_id]['data'],
                'dir': args['order'][i]['dir']
            })
        options['order'] = order

        rows, total, filtered_total = self.get_queryset(**options)
        data = []

        for row in rows:
            row_data = {}
            for column in columns:
                callback = getattr(self, 'process_%s' % column['data'],
                                   lambda row, val: val)
                val = getattr(row, column['data'], None)
                row_data[column['data']] = callback(row, val)
            data.append(row_data)

        return jsonify(recordsTotal=total,
                       recordsFiltered=filtered_total,
                       data=data)


class PermissionRequiredMixin(object):

    permission_required = None

    def get_permission_required(self):
        if self.permission_required is None:
            raise RuntimeError('permission_required was not set')
        return self.permission_required

    def check_permissions(self):
        raise NotImplementedError

    def dispatch_request(self, *args, **kwargs):
        if not user.is_authenticated:
            return app.login_manager.unauthorized()
        if not self.check_permissions():
            return Response(status=403)
            # abort(403)
        return super(PermissionRequiredMixin, self).dispatch_request(
            *args, **kwargs)
