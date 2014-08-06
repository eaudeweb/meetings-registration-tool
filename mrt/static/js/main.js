$(function () {

    $(".autosize").autosize();

    $(".select").select2();

    $("[data-toggle=delete]").on("click", function () {
        var msg = $(this).data("message");
        if (confirm(msg)) {
            var url = $(this).data("href");
            $.ajax({
                type: "DELETE",
                url: url,
                success: function (resp) {
                    if(resp.status == "success") {
                        window.location.replace(resp.url);
                    }
                    else if(resp.status == "error") {
                        alert(resp.message);
                    }
                }
            });
        }
    });

});
