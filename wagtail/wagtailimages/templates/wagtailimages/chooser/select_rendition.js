function(modal) {
    var left = $('form input[name="left"]', modal.body),
        top = $('form input[name="top"]', modal.body),
        right = $('form input[name="right"]', modal.body),
        bottom = $('form input[name="bottom"]', modal.body);


    $(".crop-image img", modal.body).Jcrop({
        onSelect: function(data) {
            left.attr({value: data.x});
            top.attr({value: data.y});
            right.attr({value: data.x2});
            bottom.attr({value: data.y2});
        }
    });

    $('form', modal.body).submit(function() {
        var formdata = new FormData(this);

        $.post(this.action, $(this).serialize(), function(response){
            modal.loadResponseText(response);
        }, 'text');

        return false;
    });
}
