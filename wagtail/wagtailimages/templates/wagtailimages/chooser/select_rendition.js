function(modal) {
    // some large images are scaled down when displayed, so we need to account
    // for that
    var trueSize;
    $(".crop-image img", modal.body).each(function(n, el) {
        trueSize = [parseInt($(el).attr('width')),
                    parseInt($(el).attr('height'))];
    });

    var left = $('form input[name="left"]', modal.body),
        top = $('form input[name="top"]', modal.body),
        right = $('form input[name="right"]', modal.body),
        bottom = $('form input[name="bottom"]', modal.body);


    // create a way to refer to the JCrop API
    var jcapi;

    $(".crop-image img", modal.body).Jcrop({
        trueSize: trueSize
    }, function() {
        jcapi = this;
    });

    var ratio_re = /(\d+):(\d+)/;
    // change aspect ratio based on the radio selections
    $('form input[name="aspect-ratio"]', modal.body).change(function(event) {
        var match = ratio_re.exec(event.target.value);

        if (match) {
            jcapi.setOptions({
                aspectRatio: parseInt(match[1]) / parseInt(match[2])
            });
        }
    });

    var form = $('form', modal.body);

    function clearForm() {
        left.removeAttr('value');
        top.removeAttr('value');
        right.removeAttr('value');
        bottom.removeAttr('value');
    };

    function applyCropValues() {
        var data = jcapi.tellSelect();

        if (data.w == 0 || data.h == 0) {
            clearForm();
        } else {
            left.attr({value: Math.round(data.x)});
            top.attr({value: Math.round(data.y)});
            right.attr({value: Math.round(data.x2)});
            bottom.attr({value: Math.round(data.y2)});
        }
    };

    $('form input.crop-button').click(applyCropValues);
    $('form input.skip-button').click(clearForm);

    $('form', modal.body).submit(function(event) {
        var formdata = new FormData(this);

        $.post(this.action, $(this).serialize(), function(response){
            modal.loadResponseText(response);
        }, 'text');

        return false;
    });
}
