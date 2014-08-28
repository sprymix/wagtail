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
            bottom = $('form input[name="bottom"]', modal.body),
            force_selection = $('form input[name="force_selection"]', modal.body);

        // Jcrop settings
        jc_settings = {
            trueSize: trueSize
        };

        // create a way to refer to the JCrop API
        var jcapi;

        var ratio_re = /(\d+):(\d+)/,
            ratio_radio = $('form input[name="aspect-ratio"]', modal.body);

        function get_aspect_ratio(raw_value) {
            var match = ratio_re.exec(raw_value);

            if (match) {
                return parseInt(match[1]) / parseInt(match[2]);
            } else {
                return null;
            }
        }

        jc_settings.aspectRatio = get_aspect_ratio(
                                        ratio_radio.filter(':checked').val())

        // change aspect ratio based on the radio selections
        ratio_radio.change(function(event) {
            jcapi.setOptions({
                aspectRatio: get_aspect_ratio(event.target.value)
            });
        });

        var form = $('form', modal.body);

        function clearForm() {
            left.attr({value: 0});
            top.attr({value: 0});
            right.attr({value: trueSize[0]});
            bottom.attr({value: trueSize[1]});
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

        // we may have a pre-selected cropping window
        if (left.val() != null && right.val() != null
                && top.val() != null && bottom.val() != null) {

            if (left.val() == right.val() && top.val() == bottom.val()) {
                clearForm();
            } else {
                jc_settings.setSelect = [parseInt(left.val()),
                                         parseInt(top.val()),
                                         parseInt(right.val()),
                                         parseInt(bottom.val())]
            }
        }

        $('form input.crop-button').click(applyCropValues);
        $('form input.skip-button').click(clearForm);

        $('form', modal.body).submit(function(event) {
            var formdata = new FormData(this);

            $.post(this.action, $(this).serialize(), function(response){
                modal.loadResponseText(response);
            }, 'text');

            return false;
        });

        // we may have preselected aspect ratio
        if (force_selection.val() == 'True') {
            jc_settings.onRelease = function() {
                this.animateTo([0, 0, trueSize[0], trueSize[1]]);
            };
        }

        $(".crop-image img", modal.body).Jcrop(jc_settings, function() {
            jcapi = this;
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
