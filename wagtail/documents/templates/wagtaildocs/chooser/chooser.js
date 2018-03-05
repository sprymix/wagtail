{% load i18n %}
function(modal) {
    function ajaxifyLinks (context) {
        $('a.document-choice', context).on('click', function() {
            modal.loadUrl(this.href);
            return false;
        });

        $('.pagination a', context).on('click', function() {
            var page = this.getAttribute("data-page");
            setPage(page);
            return false;
        });
    };

    var searchUrl = $('form.document-search', modal.body).attr('action');
    function search() {
        $.ajax({
            url: searchUrl,
            data: {
                q: $('#id_q').val(),
                collection_id: $('#collection_chooser_collection_id').val()
            },
            success: function(data, status) {
                $('#search-results').html(data);
                ajaxifyLinks($('#search-results'));
            }
        });
        return false;
    };
    function setPage(page) {

        if($('#id_q').val().length){
            dataObj = {q: $('#id_q').val(), p: page};
        }else{
            dataObj = {p: page};
        }

        $.ajax({
            url: searchUrl,
            data: dataObj,
            success: function(data, status) {
                $('#search-results').html(data);
                ajaxifyLinks($('#search-results'));
            }
        });
        return false;
    }

    ajaxifyLinks(modal.body);

    $('form.document-search', modal.body).on('submit', search);

    $('#id_q').on('input', function() {
        clearTimeout($.data(this, 'timer'));
        var wait = setTimeout(search, 50);
        $(this).data('timer', wait);
    });

    $('#collection_chooser_collection_id').on('change', search);

    {% url 'wagtailadmin_tag_autocomplete' as autocomplete_url %}
    $('#id_tags', modal.body).tagit({
        autocomplete: {source: "{{ autocomplete_url|addslashes }}"}
    });

    /* Create a function for adding image widgets (e.g. used together with
       drag/drop). */
    window.add_select_doc_widget = function() {
        $('form.doc-select', modal.body).submit(function() {
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
                        errorThrown = 'The document is too large, please upload a smaller file.';
                    }

                    var li = $('form.doc-select li:has(.file_field)',
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
