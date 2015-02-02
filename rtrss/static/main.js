function make_mailto_link(strTo, strSubject, strBody) {
    var mailto_link = "mailto:" + strTo + "?subject=" +
            encodeURIComponent(strSubject) +
            "&body=" + encodeURIComponent(strBody);
    return mailto_link;
}

$(function(){
    $('.fblink').attr('href', make_mailto_link(
        'rsstort' + '@' + 'gmail.com',
        'По поводу Rutracker RSS',
        ''
    ));
});
