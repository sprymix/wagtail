{% load i18n %}
function(modal) {
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

    function fetchResults(requestData) {
        $.ajax({
            url: searchUrl,
            data: requestData,
            success: function(data, status) {
                $('#image-results').html(data);
                ajaxifyLinks($('#image-results'));
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

    $('form.image-search', modal.body).on('submit', search);

    $('#id_q').on('input', function() {
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

    {% url 'wagtailadmin_tag_autocomplete' as autocomplete_url %}

    /* Add tag entry interface (with autocompletion) to the tag field of the image upload form */
    $('#id_tags', modal.body).tagit({
        autocomplete: {source: "{{ autocomplete_url|addslashes }}"}
    });

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
                success: function(response){
                    modal.loadResponseText(response);
                },
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
}
