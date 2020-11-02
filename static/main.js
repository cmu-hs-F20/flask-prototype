function initPage(){

    $('.geo_input').each(function(){
        $(this).autocomplete({
            source: JSON.parse($(this).attr('autocomplete_list')),
            autoFocus: true
        });
    });

    $('#state').keyup(function(){
        var matches_state = $.inArray($(this).val(), JSON.parse($(this).attr('autocomplete_list'))) > -1;
        // alert('Test messsage!' + matches_state)
        
        $('#county').attr('disabled', !matches_state);
        if(!matches_state){
            $('#county').val('');
        }
        
        if(matches_state){
            $.post('counties-list',
            {
                state: $(this).val()
            }, function(response){
                $('#county').autocomplete("option", {source: JSON.parse(response)});
            });
        }

    });


    $("#addgeo").submit(function(event){
        event.preventDefault();
    
        var id = function(){
            var ids = $('#statesList').children().map(function(){
                return parseInt($(this).attr('id'));
            }).get();
    
            var id = Math.max(...ids, 0) + 1;

            return String(id);
        }();
        
        // todo: don't add if request fails
        $.post('register-geo', {
            state: $('#state').val(),
            county: $('#county').val(),
            id: id
        }, function(response){
            $('#statesList').append(response);
            $('#state').val('').focus();
            $('#county').val('');
            // $('#state').focus()
        })
        .fail(function(response){
            alert('Error: ' + response.responseText);
        });
    });

    $("#statesList").on('click', 'a', function(event){
        var id = $(this).parent().attr('id');

        $.post('drop-geo',
            {
                id:id
            });

        $(this).parent().hide();
    });

    // todo: less ugly, please
    $('#statesList').on(
        {
            mouseenter: function(){
                $(this).css('background-color', '#ff0000');
            },
            mouseleave: function(){
                $(this).css('background-color', '#ffffff');
            }
        }, 'a');
}