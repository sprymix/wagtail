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
          crop_b.attr({'data-original-image-id': imageData.original_id});
          crop_b.attr({'data-spec': imageData.spec});
        } else {
          chooserElement.addClass('blank');
        }
    });

    $('.action-choose', chooserElement).click(function() {
        ModalWorkflow({
            'url': window.chooserUrls.imageChooser + '?select_rendition=True',
            'responses': {
                'imageChosen': function(imageData) {
                    input.val(imageData.id).trigger('change', imageData);
                }
            }
        });
    });

    crop_b.click(function() {
        // from original image id and crop spec construct a new URL
        var spec = $(this).attr('data-spec').replace('crop-', '')
                                            .replace(':', ','),
            url = [window.chooserUrls.imageChooser,
                   $(this).attr('data-original-image-id'),
                   '/select_rendition/?crop=', spec
                   ].join('');

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
