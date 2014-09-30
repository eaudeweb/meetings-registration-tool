$(function () {

    var job_list = $('#job-list');
    var job_status_url = job_list.data('job-status-url');

    var FAILED = 'failed';
    var FINISHED = 'finished';
    var STATUS = {
        FAILED: 'Failed',
        FINISHED: 'Finished'
    }

    var Job = function (id) {
        if (!(this instanceof Job)) {
            return new Job(id);
        }
        this.id = id;
    };

    Job.prototype.finish = function (result) {
        var job_row = $('#' + this.id);
        job_row.addClass('success');
        job_row.find('.status').text(STATUS.FINISHED);
        var html = $('<a>').attr('href', result).text('Download file');
        job_row.find('.result').html(html);
    };

    Job.prototype.failed = function () {
        var job_row = $('#' + this.id);
        job_row.addClass('danger');
        job_row.find('.status').text(STATUS.FAILED);
    };


    var _addStatusCheck = function (job) {
        $.doTimeout(job.id, 2000, function () {
            var req = $.getJSON(job_status_url, {'job_id': job.id});
            req.done(function (resp) {
                if(resp.status == FINISHED) {
                    $.doTimeout(job.id);
                    job.finish(resp.result);
                }
                if(resp.status == FAILED) {
                    $.doTimeout(job.id);
                    job.failed();
                }
            }).fail(function () {
                $.doTimeout(job.id);
                job.failed();
            });
            return true;
        });

    }

    var Queue = (function () {

        return {
            addJob: function (jobid) {
                _addStatusCheck(jobid);
            }
        }

    })();

    job_list.find('tr.job').each(function () {
        var jobid = $(this).find('.jobid').text();
        var job_status = $(this).find('.status').text().toLowerCase();
        if(jobid && $.inArray(job_status, [FAILED, FINISHED]) < 0) {
            var job = Job(jobid);
            Queue.addJob(job);
        }
    });

    var printout_count = $('.printout-count');
    if(printout_count.length > 0) {
        var url = printout_count.data('url');
        $.getJSON(url, function (data) {
            if(data.count !=0) {
                printout_count.removeClass('hide');
                printout_count.find('.badge').text(data.count);
                printout_count.find('.badge').attr('title', data.title);
            }
        });
    }

    $('#infinite-scroll-container .printout-item-container').infinitescroll({
        nextSelector: '#infinite-scroll-container .pagination a.next',
        navSelector: '#infinite-scroll-container .pagination',
        itemSelector: '#infinite-scroll-container .printout-table ',
        loading: {
            finishedMsg: '',
            msgText: '',
            selector: '#infinite-scroll-container .printout-loading'
        }
    }, function (newElements, data, url) {
        $(newElements).find('.column-headers').hide();
        $(newElements).find('.group').each(function () {
            var id = $(this).data('id');
            if($('[data-id=' + id +']').length > 1) {
                $(this).parents('tr').hide();
            }
        });
        $(this).append(newElements);
    });

});
