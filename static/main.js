$(document).ready(function(){
    $("#addgeo").submit(function(event){
        event.preventDefault();
        
        var state = $('#state').val();

        var $form= $(this),
            url = 'register-geo';
        
            
        var id = function(){
            var ids = $('#statesList').children().map(function(){
                return parseInt($(this).attr('id'))
            }).get();
    
            var id = Math.max(...ids, 0) + 1

            return String(id)
        }();

        
        // todo: don't add if request fails
        var posting = $.post(url, {
            state: state,
            id: id
        }, function(response){
            $('#statesList').append(response);
        })
        .fail(function(response){
            alert('Error: ' + response.responseText)
        })
    });

    $(".selected-state > a").click(function(event){
        var id = $(this).parent().attr('id')

        $.post('drop-geo',
            {
                id:id
            });

        $(this).parent().hide()
    });

});