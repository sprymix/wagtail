IMAGE_CHOOSER_MODAL_ONLOAD_HANDLERS = {
    'chooser': function(modal, jsonData) {
        var searchUrl = $('form.image-search', modal.body).attr('action');

        /* currentTag stores the tag currently being filtered on, so that we can
        preserve this when paginating */
        var currentTag;

        function ajaxifyLinks (context) {
            $('.listing a', context).on('click', function() {
                modal.loadUrl(this.href);
                return false;
            });

            $('.pagination a', context).on('click', function() {
                var page = this.getAttribute("data-page");
                setPage(page);
                return false;
            });
        }
        var request;

        function fetchResults(requestData) {
            request = $.ajax({
                url: searchUrl,
                data: requestData,
                success: function(data, status) {
                    request = null;
                    $('#image-results').html(data);
                    ajaxifyLinks($('#image-results'));
                },
                error: function() {
                    request = null;
                }
            });
        }

        function search() {
            /* Searching causes currentTag to be cleared - otherwise there's
            no way to de-select a tag */
            currentTag = null;
            fetchResults({
                q: $('#id_q').val(),
                collection_id: $('#collection_chooser_collection_id').val()
            });
            return false;
        }

        function setPage(page) {
            params = {p: page};
            if ($('#id_q').val().length){
                params['q'] = $('#id_q').val();
            }
            if (currentTag) {
                params['tag'] = currentTag;
            }
            params['collection_id'] = $('#collection_chooser_collection_id').val();
            fetchResults(params);
            return false;
        }

        ajaxifyLinks(modal.body);

        // $('form.image-upload', modal.body).on('submit', function() {
        //     var formdata = new FormData(this);

        //     if ($('#id_image-chooser-upload-title', modal.body).val() == '') {
        //         var li = $('#id_image-chooser-upload-title', modal.body).closest('li');
        //         if (!li.hasClass('error')) {
        //             li.addClass('error');
        //             $('#id_image-chooser-upload-title', modal.body).closest('.field-content').append('<p class="error-message"><span>This field is required.</span></p>')
        //         }
        //         setTimeout(cancelSpinner, 500);
        //     } else {
        //         $.ajax({
        //             url: this.action,
        //             data: formdata,
        //             processData: false,
        //             contentType: false,
        //             type: 'POST',
        //             dataType: 'text',
        //             success: modal.loadResponseText,
        //             error: function(response, textStatus, errorThrown) {
        //                 message = jsonData['error_message'] + '<br />' + errorThrown + ' - ' + response.status;
        //                 $('#upload').append(
        //                     '<div class="help-block help-critical">' +
        //                     '<strong>' + jsonData['error_label'] + ': </strong>' + message + '</div>');
        //             }
        //         });
        //     }

        //     return false;
        // });

        $('form.image-search', modal.body).on('submit', search);

        $('#id_q').on('input', function() {
            if (request) {
                request.abort();
            }
            clearTimeout($.data(this, 'timer'));
            var wait = setTimeout(search, 200);
            $(this).data('timer', wait);
        });
        $('#collection_chooser_collection_id').on('change', search);
        $('a.suggested-tag').on('click', function() {
            currentTag = $(this).text();
            $('#id_q').val('');
            fetchResults({
                'tag': currentTag,
                collection_id: $('#collection_chooser_collection_id').val()
            });
            return false;
        });

        function populateTitle(context) {
            var fileWidget = $('#id_image-chooser-upload-file', context);
            fileWidget.on('change', function () {
                var titleWidget = $('#id_image-chooser-upload-title', context);
                var title = titleWidget.val();
                if (title === '') {
                    // The file widget value example: `C:\fakepath\image.jpg`
                    var parts = fileWidget.val().split('\\');
                    var fileName = parts[parts.length - 1];
                    titleWidget.val(fileName);
                }
            });
        }

        function humanReadableTitle(titleString) {
            return titleString.replace(/\.[a-zA-Z]+$/, '').replaceAll(/[_\-]/g, ' ');
        }

        populateTitle(humanReadableTitle(modal.body));

        /* Create a function for adding image widgets (e.g. used together with
        drag/drop). */
        window.add_select_image_widget = function() {
            $('form.image-select', modal.body).submit(function() {
                var formdata = new FormData(this);
                $.ajax({
                    url: this.action,
                    data: formdata,
                    processData: false,
                    contentType: false,
                    type: 'POST',
                    dataType: 'text',
                    success: modal.loadResponseText,
                    error: function(xhr, textStatus, errorThrown) {
                        // Display the error in the upload form
                        if (xhr.status == 413) {
                            // make the error message for large files user-friendly
                            errorThrown = 'The image is too large, please upload a smaller file.';
                        }

                        var li = $('form.image-select li:has(.image_field)',
                                modal.body),
                            err = li.find('p.error-message')
                        li.addClass('error');

                        // if we already have an error-message element, write into it
                        if (err.length) {
                            err.html(errorThrown);
                        } else {
                            // add a <p class="error-message">...</p> to the image_field
                            li.find('.field-content').append(
                                '<p class="error-message">' + errorThrown + '</p>');
                        }
                    }
                });

                return false;
            });
        };
    },
    'image_chosen': function(modal, jsonData) {
        modal.respond('imageChosen', jsonData['result']);
        modal.close();
    },
    'select_format': function(modal) {
        $('form', modal.body).on('submit', function() {
            var formdata = new FormData(this);

            $.post(this.action, $(this).serialize(), modal.loadResponseText, 'text');

            return false;
        });
    },
    'select_rendition': function(modal) {
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
                // if the value is 0 or equivalent, make the width and height fields
                // blank
                if (!parseInt(width.val())) {
                    width.val('');
                    height.val('');
                } else {
                    if (jcapi) {
                        var data = jcapi.tellSelect(),
                            ratio = parseInt(data.w) / parseInt(data.h);
    
                        if (ratio) {
                            height.val(Math.round(parseInt(width.val() || 0) / ratio));
                        }
                    }
                }
            }
            function _heightChange() {
                // if the value is 0 or equivalent, make the width and height fields
                // blank
                if (!parseInt(height.val())) {
                    width.val('');
                    height.val('');
                } else {
                    if (jcapi) {
                        var data = jcapi.tellSelect(),
                            ratio = data.w / data.h;
                        if (ratio) {
                            width.val(Math.round(parseInt(height.val() || 0) * ratio));
                        }
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
                var action = form.attr('action'),
                    formdata = new FormData(this);
    
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
    
};
