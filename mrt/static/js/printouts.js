var Queue = (function () {

    var Job = function (id, name) {
        if (!(this instanceof Job)){
            return new Job(id, name);
        }
        this.id = id;
        this.name = name;
    }

    Job.prototype.is_rendered = function() {
        return $('#' + this.id).length > 0 ? true : false;
    };

    Job.prototype.render = function () {
        var job = this;
        var template = $('#printout-job-tmpl').html();
        var data = {'id': this.id, 'name': this.name};
        var $html = $(Mustache.render(template, data));

        // add events
        $html.on('click', '.job-close', function () {
            var url = $(this).data('href');
            $.get(url, {'job_id': job.id}, $.proxy(function () {
                $(this).slideUp('fast');
            }), this);
        });

        return $html;
    }

    Job.prototype.finish = function (result) {
        var finished_template = $('#printout-job-finished-tmpl').html();
        var $job = $('#' + this.id);
        $job.addClass('bg-success');
        data = {'name': this.name, 'href': result};
        $job.html(Mustache.render(finished_template, data));
    }

    Job.prototype.failed = function () {
        var failed_template = $('#printout-job-failed-tmpl').html();
        var $job = $('#' + this.id);
        $job.addClass('bg-danger');
        data = {'name': this.name};
        $job.html(Mustache.render(failed_template, data));
    }


    this.queue = [];

    var job_status_url = window.JOB_STATUS_URL;

    var _addStatusCheck = function (job) {

        $.doTimeout(job.id, 2000, $.proxy(function () {
            var req = $.getJSON(job_status_url, {'job_id': job.id});
            req.done(function (resp) {
                if(resp.status == 'finished') {
                    $.doTimeout(job.id);
                    job.finish(resp.result);
                }
                if(resp.status == 'failed') {
                    $.doTimeout(job.id);
                    job.failed();
                }
            }).fail(function () {
                $.doTimeout(job.id);
                job.failed();
            });
            return true;
        }));

    };

    return {
        addJob: $.proxy(function (job_id, job_name) {
            var job = Job(job_id, job_name);
            this.queue.push(job);
            _addStatusCheck(job);
        }, this),

        render: $.proxy(function () {
            if($('.queue').length == 0) {
                $('<div>').attr('class', 'queue').appendTo('body');
            }
            var container = $('.queue');
            $.each(this.queue, function (i, job) {
                if(!job.is_rendered()) {
                    container.append(job.render());
                }
            });
        }, this)
    }

})();

$(function () {

    $('.btn-download').on('click', function () {
        $.post().done(function (data) {
            Queue.addJob(data.job_id, data.job_name);
            Queue.render();
        });
    });

});
