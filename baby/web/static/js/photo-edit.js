
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(function () {
    // открыть модалку редактирования фото
    console.log($('.photo-wrap'))
    $('.photo-wrap').append('<span class="photo-wrap-open-edit icon-pencil-1"></span>');

    $('.photo-wrap').click(function () {
        var url = $(this).attr('url');
        var data_id = $(this).attr('data-id');
        var items =
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: left top;"></div>' +
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: center top;"></div>'+
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: right top;"></div>'+

                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: left center;"></div>' +
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: center center;"></div>'+
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: right center;"></div>'+

                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: left bottom;"></div>' +
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: center bottom;"></div>'+
                   '<div class="photo-wrap photo-edit" data-id="'+data_id+'" style="background-image:url('+url+'); background-size: cover; background-position: right bottom;"></div>'

        $('#photo-edit-modal-list').html(items);
        $('#photo-edit-modal').modal({fadeDuration: 100});
    });

    // сохранить выбранный вариант фото
    $(document).on('click','.photo-edit',function(){
        var data_id = $(this).attr('data-id')
        var background_position = $(this).css('background-position');
        var csrftoken = getCookie('csrftoken');
        $.post('/album/photo/'+data_id + '/', {
            'csrfmiddlewaretoken': csrftoken,
            'background_position': background_position
        }, function (data) {
            $('.photo-wrap[data-id='+data_id+']').css('background-position', background_position);
            $('#photo-edit-modal .close-modal').click();
        });
    });

});