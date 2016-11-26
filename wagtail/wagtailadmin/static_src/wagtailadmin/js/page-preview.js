"use strict";

function createPreviewButtonHandler(form, button) {
    var $this = button;
    var previewWindow;

    /* Handler for page preview button click */
    return function(e) {
        e.preventDefault();

        if (previewWindow) {
            previewWindow.close();
        }

        previewWindow = window.open($this.data('placeholder'), $this.data('windowname'));

        if (previewWindow.addEventListener) {
            previewWindow.addEventListener('load', function() {
                submitPreview.call($this, true);
            }, false);
        } else if (previewWindow.attachEvent) {
            // for IE
            previewWindow.attachEvent('onload', function() {
                submitPreview.call($this, true);
            }, false);
        } else {
            // Can't trap onload event, so load contents immediately without fancy effects
            submitPreview.call($this, false);
        }

        function submitPreview(enhanced) {
            var previewDoc = previewWindow.document;

            $.ajax({
                type: 'POST',
                url: $this.data('action'),
                data: form.serialize(),
                success: function(data, textStatus, request) {
                    if (request.getResponseHeader('X-Wagtail-Preview') == 'ok') {
                        if (enhanced) {
                            var frame = previewDoc.getElementById('preview-frame');

                            frame = frame.contentWindow || frame.contentDocument.document || frame.contentDocument;
                            frame.document.open();
                            frame.document.write(data);
                            frame.document.close();

                            var hideTimeout = setTimeout(function() {
                                previewDoc.getElementById('loading-spinner-wrapper').className += ' remove';
                                clearTimeout(hideTimeout);
                            });

 // just enough to give effect without adding discernible slowness
                        } else {
                            previewDoc.open();
                            previewDoc.write(data);
                            previewDoc.close();
                        }

                    } else {
                        previewWindow.close();
                        disableDirtyFormCheck();
                        document.open();
                        document.write(data);
                        document.close();
                    }
                },

                error: function(xhr, textStatus, errorThrown) {
                    /* If an error occurs, display it in the preview window so that
                    we aren't just showing the spinner forever. We preserve the original
                    error output rather than giving a 'friendly' error message so that
                    developers can debug template errors. (On a production site, we'd
                    typically be serving a friendly custom 500 page anyhow.) */

                    previewDoc.open();
                    previewDoc.write(xhr.responseText);
                    previewDoc.close();
                }
            });
        }

    }
}
