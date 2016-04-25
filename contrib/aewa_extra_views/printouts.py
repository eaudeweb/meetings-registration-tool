
from contrib.cites_extra_views.printouts import _process_verification
from contrib.cites_extra_views.printouts import VerificationList as _VerificationList
from flask import request, redirect, url_for
from mrt.common.printouts import _add_to_printout_queue
from mrt.meetings.printouts import _process_provisional_list
from mrt.meetings.printouts import ProvisionalList as _ProvisionalList


class ProvisionalList(_ProvisionalList):

    def post(self):
        flag = request.args.get('flag')
        title = self.TITLE_MAP.get(flag, self.DOC_TITLE)
        template_name = 'printouts_aewa/_provisional_list_pdf.html'
        _add_to_printout_queue(_process_provisional_list, self.JOB_NAME,
                               title, flag, template_name)
        return redirect(url_for('.printouts_provisional_list', flag=flag))


class VerificationList(_VerificationList):

    def post(self):
        category_ids = request.args.getlist('categories')
        template_name = 'printouts_aewa/_verification_table_pdf.html'
        _add_to_printout_queue(_process_verification, self.JOB_NAME,
                               self.DOC_TITLE, category_ids,
                               template_name)
        return redirect(url_for('.printouts_verification',
                                categories=category_ids))
