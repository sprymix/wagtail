"use strict";

function createPreviewButtonHandler(form, button) {
    var $this = button;

    /* Handler for page preview button click */
    return function(e) {
        e.preventDefault();

        var previewWindow = window.open($this.data('placeholder'), $this.data('windowname'));

        function submitPreview(enhanced){
            // save the tinyMCE data if present
            if (tinyMCE) {
                tinyMCE.triggerSave();
            }

            $.ajax({
                type: "POST",
                url: $this.data('action'),
                data: form.serialize(),
                success: function(data, textStatus, request) {
                    if (request.getResponseHeader('X-Wagtail-Preview') == 'ok') {
                        var pdoc = previewWindow.document;

                        if(enhanced){
                            var frame = pdoc.getElementById('preview-frame');

                            frame = frame.contentWindow || frame.contentDocument.document || frame.contentDocument;
                            frame.document.open();
                            frame.document.write(data);
                            frame.document.close();

                            var hideTimeout = setTimeout(function(){
                                pdoc.getElementById('loading-spinner-wrapper').className += 'remove';
                                clearTimeout(hideTimeout);
                            }) // just enough to give effect without adding discernible slowness
                        } else {
                            pdoc.open();
                            pdoc.write(data);
                            pdoc.close()
                        }
                    } else {
                        previewWindow.close();
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

                    previewWindow.document.open();
                    previewWindow.document.write(xhr.responseText);
                    previewWindow.document.close();
                }
            });
        }

        if(/MSIE/.test(navigator.userAgent)){
            submitPreview.call($this, false);
        } else {
            previewWindow.onload = function(){
                submitPreview.call($this, true);
            }
        }
    }
}

