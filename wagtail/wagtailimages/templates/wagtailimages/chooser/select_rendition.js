function(modal) {
    function attach_jcrop() {
        // Some large images are scaled down when displayed, so we need to account
        // for that.
        var trueSize, pps_re = /pps=[^\&]*/g;
        var form = $('form', modal.body);

        $(".crop-image img", modal.body).each(function(n, el) {
            trueSize = [parseInt($(el).attr('width')),
                        parseInt($(el).attr('height'))];
        });

        // prevent pressing "enter" from submitting the form
        form.bind('keypress', function (e) {
            if (e.keyCode == 13) {
                return false;
            }
        });

        var left = $('form input[name="left"]', modal.body),
            top = $('form input[name="top"]', modal.body),
            right = $('form input[name="right"]', modal.body),
            bottom = $('form input[name="bottom"]', modal.body),
            force_selection = $('form input[name="force_selection"]', modal.body),
            width = $('form input[name="width"]', modal.body),
            height = $('form input[name="height"]', modal.body),
            area_size = $('.cropped-area .area-size', modal.body);

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


        function _widthChange() {
            if (jcapi) {
                var data = jcapi.tellSelect(),
                    ratio = data.w / data.h;
                if (ratio) {
                    height.val(Math.round(parseInt(width.val() || 0) / ratio));
                }
            }
        }
        function _heightChange() {
            if (jcapi) {
                var data = jcapi.tellSelect(),
                    ratio = data.w / data.h;
                if (ratio) {
                    width.val(Math.round(parseInt(height.val() || 0) * ratio));
                }
            }
        }

        // react to updates to width & height
        width.on('input', _widthChange);
        height.on('input', _heightChange);

        // change aspect ratio based on the radio selections
        ratio_radio.change(function(event) {
            jcapi.setOptions({
                aspectRatio: get_aspect_ratio(event.target.value)
            });
            _widthChange();
        });

        // helper function to display current selection
        function showAreaSelection(data) {
            data = data || jcapi.tellSelect();
            if (data && data.w && data.h) {
                area_size.text(parseInt(data.w) + ' x ' + parseInt(data.h));
                _widthChange();
            } else {
                area_size.text('n/a');
            }
        };

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
        $('form input.clear-button').click(function() {
            jcapi.release();
        });

        form.submit(function(event) {
            // if the user has specified a "fit" restriction, replace any prior
            // "pps" with fit-WxH
            var action = form.attr('action');
            if (height.val() && width.val()) {
                    var fit = 'forcefit-' + width.val() + 'x' + height.val();
                if (pps_re.test(form.attr('action'))) {
                    action = action.replace(/pps=[^\&]*/g, 'pps=' + fit);
                } else {
                    if (/\?/g.test(action)) {
                        action = action + '&' + fit;
                    } else {
                        action = action + '?' + fit;
                    }
                }
            }

            var formdata = new FormData(this);

            $.post(action, $(this).serialize(), function(response){
                modal.loadResponseText(response);
            }, 'text');

            return false;
        });

        // we may have preselected aspect ratio
        if (force_selection.val() == 'True') {
            jc_settings.onRelease = function() {
                this.animateTo([0, 0, trueSize[0], trueSize[1]]);
            };
            jc_settings.setSelect = jc_settings.setSelect ||
                                        [0, 0, trueSize[0], trueSize[1]];
        } else {
            jc_settings.onRelease = function() {
                showAreaSelection({w:0, h:0});
            }
        }
        jc_settings.onSelect = showAreaSelection;
        jc_settings.onChange = showAreaSelection;

        $(".crop-image img", modal.body).Jcrop(jc_settings, function() {
            jcapi = this;
            showAreaSelection();
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
