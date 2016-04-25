$(function() {
    // Redirect users that don't support filereader
    if (!$('html').hasClass('filereader')) {
        document.location.href = window.fileupload_opts.simple_upload_url;
        return false;
    }

    // prevents browser default drag/drop
    if (!$('html').hasClass('dragdrop_override')) {
        $(document).bind('drop dragover', function (e) {
            // the delegated events should still be propagated
            if (!e.delegatedEvent) {
              e.preventDefault();
            }
        });
        $('html').addClass('dragdrop_override');
    }

    window.add_file_upload_widget = function(main_el, options) {
        options = options || {};
        var oneFileUploaded = false,
            oneFileOnly = options.oneFileOnly;
        var dropZone = $('.drop-zone', main_el);

        function _oneFileOnlyPicked() {
            if (oneFileUploaded) {
                return true;
            } else {
                oneFileUploaded = true;
                dropZone.hide(400);
                $('.upload-list', main_el).children().remove();
                return false;
            }
        }

        function _oneFileOnlyClear() {
            oneFileUploaded = false;
            dropZone.show(400);
        }

        options = $.extend({
            dataType: 'html',
            sequentialUploads: true,
            dropZone: dropZone,
            acceptFileTypes: options.accepted_file_types,
            maxFileSize: options.max_file_size,
            previewMinWidth:150,
            previewMaxWidth:150,
            previewMinHeight:150,
            previewMaxHeight:150,
            messages: {
                acceptFileTypes: options.errormessages.accepted_file_types,
                maxFileSize: options.errormessages.max_file_size
            },

            add: function (e, data) {
                // special processing for one file only uploads
                if (oneFileOnly) {
                    if (_oneFileOnlyPicked()) {
                        return;
                    };
                }

                var $this = $(this);
                var that = $this.data('blueimp-fileupload') || $this.data('fileupload')
                var li = $($('.upload-list-item', main_el).html()).addClass('upload-uploading')
                var options = that.options;

                $('.upload-list', main_el).append(li);
                data.context = li;

                data.process(function () {
                    return $this.fileupload('process', data);
                }).always(function () {
                    data.context.removeClass('processing');
                    data.context.find('.left').each(function(index, elm){
                        $(elm).append(data.files[index].name);
                    });
                    data.context.find('.preview .thumb').each(function (index, elm) {
                        $(elm).addClass('hasthumb')
                        $(elm).append(data.files[index].preview);
                    });
                }).done(function () {
                    data.context.find('.start').prop('disabled', false);
                    if ((that._trigger('added', e, data) !== false) &&
                            (options.autoUpload || data.autoUpload) &&
                            data.autoUpload !== false) {
                        data.submit();
                    }
                }).fail(function () {
                    // special processing for one file only uploads
                    if (oneFileOnly) {
                        _oneFileOnlyClear();
                    }

                    if (data.files.error) {
                        data.context.each(function (index) {
                            var error = data.files[index].error;
                            if (error) {
                                $(this).find('.error_messages').text(error);
                            }
                        });
                    }
                });
            },

            processfail: function(e, data){
                var itemElement = $(data.context);
                itemElement.removeClass('upload-uploading').addClass('upload-failure');
            },

            progress: function (e, data) {
                if (e.isDefaultPrevented()) {
                    return false;
                }

                var progress = Math.floor(data.loaded / data.total * 100);
                data.context.each(function () {
                    $(this).find('.progress').addClass('active').attr('aria-valuenow', progress).find('.bar').css(
                        'width',
                        progress + '%'
                    ).html(progress + '%');
                });
            },

            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $('.progress-secondary', main_el).addClass('active').attr('aria-valuenow', progress).find('.bar').css(
                    'width',
                    progress + '%'
                ).html(progress + '%');

                if (progress >= 100){
                    $('.progress-secondary', main_el).removeClass('active').find('.bar').css('width','0%');
                }
            },

            done: function (e, data) {
                var itemElement = $(data.context);
                var response = $.parseJSON(data.result);

                if(response.success){
                    itemElement.addClass('upload-success')

                    $('.right', itemElement).append(response.form);

                    // run tagit enhancement, targeting specifically
                    // the core tag field
                    $('.tag_field .input > input', itemElement).tagit(window.tagit_opts);
                } else {
                    // special processing for one file only uploads
                    if (oneFileOnly) {
                        _oneFileOnlyClear();
                    }

                    itemElement.addClass('upload-failure');
                    $('.right .error_messages', itemElement).append(response.error_message);
                }

            },

            fail: function(e, data){
                // special processing for one file only uploads
                if (oneFileOnly) {
                    _oneFileOnlyClear();
                }

                var itemElement = $(data.context);
                itemElement.addClass('upload-failure');
            },

            always: function(e, data){
                var itemElement = $(data.context);
                itemElement.removeClass('upload-uploading').addClass('upload-complete');
            }
        }, options);

        $('.fileupload', main_el).fileupload(options);

        // ajax-enhance forms added on done()
        $('.upload-list', main_el).on('submit', 'form', function(e){
            var form = $(this);
            var itemElement = form.closest('.upload-list > li');

            e.preventDefault();

            $.post(this.action, form.serialize(), function(data) {
                if (data.success) {
                    itemElement.slideUp(function(){$(this).remove()});
                }else{
                    // special processing for one file only uploads
                    if (oneFileOnly) {
                        _oneFileOnlyClear();
                    }

                    form.replaceWith(data.form);
                    // run tagit enhancement on new form, targeting specifically
                    // the core tag field
                    $('.tag_field .input > input', form).tagit(window.tagit_opts);
                }
            });
        });

        $('.upload-list', main_el).on('click', '.delete', function(e){
            var form = $(this).closest('form');
            var itemElement = form.closest('.upload-list > li');

            e.preventDefault();

            var CSRFToken = $('input[name="csrfmiddlewaretoken"]', form).val();

            $.post(this.href, {csrfmiddlewaretoken: CSRFToken}, function(data) {
                if (data.success) {
                    itemElement.slideUp(function(){$(this).remove()});

                    // special processing for one file only uploads
                    if (oneFileOnly) {
                        _oneFileOnlyClear();
                    }
                }else{

                }
            });
        });
    }
});
