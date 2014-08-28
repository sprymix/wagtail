function createImageChooser(id) {
    var chooserElement = $('#' + id + '-chooser');
    var previewImage = chooserElement.find('.preview-image img');
    var input = $('#' + id);

    $('.action-choose', chooserElement).click(function() {
        ModalWorkflow({
            'url': window.chooserUrls.imageChooser,
            'responses': {
                'imageChosen': function(imageData) {
                    input.val(imageData.id);
                    previewImage.attr({
                        'src': imageData.preview.url,
                        'width': imageData.preview.width,
                        'height': imageData.preview.height,
                        'alt': imageData.title
                    });
                    chooserElement.removeClass('blank');
                }
            }
        });
    });

    $('.action-clear', chooserElement).click(function() {
        input.val('');
        chooserElement.addClass('blank');
    });
}

function createRenditionChooser(id) {
    var chooserElement = $('#' + id + '-chooser');
    var previewImage = chooserElement.find('.preview-image img');
    var input = $('#' + id);
    var crop_b = $('input.action-recrop', chooserElement);

    input.change(function(ev, imageData) {
        if(imageData) {
          previewImage.attr({
            'src': imageData.preview.url,
            'width': imageData.preview.width,
            'height': imageData.preview.height,
            'alt': imageData.title
          });
          chooserElement.removeClass('blank');
          chooserElement.attr({'data-original-image-id': imageData.original_id});
          chooserElement.attr({'data-spec': imageData.spec});
        } else {
          chooserElement.addClass('blank');
        }
    });

    // build up the special params to be used witht he URL
    function get_params() {
        // there are many possible specs that need to be included in the URL
        var spec = chooserElement.attr('data-spec').replace('crop-', '')
                                                   .replace(':', ','),
            crop = chooserElement.attr('data-crop'),
            ratios = chooserElement.attr('data-ratios'),
            default_ratio = chooserElement.attr('data-default_ratio'),
            disable_selection = chooserElement.attr('data-disable_selection'),
            force_selection = chooserElement.attr('data-force_selection');

        // convert disable and force selection setitngs to a single char
        disable_selection = disable_selection ? disable_selection[0] : null;
        force_selection = force_selection ? force_selection[0] : null;

        var params_dict = {
            // if we specify crop it overrides spec
            crop: crop || spec,
            ratios: ratios,
            ar: default_ratio,
            fsel: force_selection,
            dsel: disable_selection
        };

        // build URL with the params_dict
        var params = [];
        $.each(params_dict, function(name, val) {
            if (val != null) {
                params.push(name, '=', encodeURIComponent(val), '&');
            }
        });
        // pop the last '&'
        params.pop();
        return params.join('');
    }

    $('.action-choose', chooserElement).click(function() {
        var additional_params = get_params();

        // build URL with the additional params
        var url = [window.chooserUrls.imageChooser,
                   '?select_rendition=True&', additional_params];
        url = url.join('');

        ModalWorkflow({
            'url': url,
            'responses': {
                'imageChosen': function(imageData) {
                    input.val(imageData.id).trigger('change', imageData);
                }
            }
        });
    });

    crop_b.click(function() {
        var additional_params = get_params(),
            image_id = chooserElement.attr('data-original-image-id');

        // build URL with the additional params
        var url = [window.chooserUrls.imageChooser, image_id,
                   '/select_rendition/?', additional_params];
        url = url.join('');

        ModalWorkflow({
            'url': url,
            'responses': {
                'imageChosen': function(imageData) {
                    input.val(imageData.id).trigger('change', imageData);
                }
            }
        });
    });

    $('.action-clear', chooserElement).click(function() {
        input.val('').trigger('change');
    });
}
