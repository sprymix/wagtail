function(modal) {
    modal.respond('pageChosen', {
        'url': '{{ url|escapejs }}',
        'title': '{{ link_text|escapejs }}',
        'new_window': {{ new_window|yesno:"true,false" }}
    });
    modal.close();
}
