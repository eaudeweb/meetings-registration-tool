$(function () {

    var template = $('#printout-job-tmpl').html();
    var finished_template = $('#printout-job-finished-tmpl').html();

    // speeds up future uses
    Mustache.parse(template);
    Mustache.parse(finished_template);

    var queue = (function () {

        this.queue = [];

        var job_status_url = window.JOB_STATUS_URL;

        var _addStatusCheck = function (job) {

            $.doTimeout(job.id, 1000, $.proxy(function () {
                var req = $.getJSON(job_status_url, {'job_id': job.id});
                req.done(function (resp) {
                    if(resp.status == 'finished') {
                        $.doTimeout(job.id, false);
                        job.finish();
                    }
                });
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
        var data = {'id': this.id, 'name': this.name};
        return $(Mustache.render(template, data));
    }

    Job.prototype.finish = function () {
        $('#' + this.id).slideUp('fast', function () {
            $(this).remove();
        });

    }

    $('.btn-download').on('click', function () {
        $.post().done(function (data) {
            queue.addJob(data.job_id, data.job_name);
            queue.render();
        });
    });

});
