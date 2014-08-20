function(modal) {
    function attach_jcrop() {
        // Some large images are scaled down when displayed, so we need to account
        // for that.
        var trueSize;

        $(".crop-image img", modal.body).each(function(n, el) {
            trueSize = [parseInt($(el).attr('width')),
                        parseInt($(el).attr('height'))];
        });

        var left = $('form input[name="left"]', modal.body),
            top = $('form input[name="top"]', modal.body),
            right = $('form input[name="right"]', modal.body),
            bottom = $('form input[name="bottom"]', modal.body);

        // Jcrop settings
        jc_settings = {
            trueSize: trueSize
        };

        // we may have a pre-selected cropping window
        var crop = '{{ crop }}'.split(',');
        if (crop.length != 4) {
            crop = null;
        } else {
            jc_settings.setSelect = crop;
        }

        // create a way to refer to the JCrop API
        var jcapi;

        var ratio_re = /(\d+):(\d+)/;
        // change aspect ratio based on the radio selections
        $('form input[name="aspect-ratio"]', modal.body).change(function(event) {
            var match = ratio_re.exec(event.target.value),
                ratio;

            if (match) {
                ratio = parseInt(match[1]) / parseInt(match[2]);
            } else {
                ratio = null;
            }
            jcapi.setOptions({
                aspectRatio: ratio
            });
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

        $(".crop-image img", modal.body).ready(function() {
            $(".crop-image img", modal.body).Jcrop(jc_settings, function() {
                jcapi = this;
            });
        });
    };

    // we need the image to load and render properly before we apply Jcrop
    // widget, so that large images are scaled correctly
    var load_check = setInterval(function() {
        if ($(".crop-image", modal.body).width() > 0) {
            clearInterval(load_check);
            attach_jcrop();
        }
    }, 50);
}
