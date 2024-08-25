<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

alert('lskdjflksdkfsdkflk');
$(document).ready(function() {
    $('#register-username').on('blur', function() {
        var username = $(this).val();
        $.ajax({
            url: '{% url "check_username" %}',  // We'll create this URL
            data: {
                'username': username
            },
            dataType: 'json',
            success: function(data) {
                if (data.is_taken) {
                    $('#username-error').text('This username is already taken.').show();
                } else {
                    $('#username-error').hide();
                }
            }
        });
    });

    $('#register-form').on('submit', function(e) {
        if ($('#username-error').is(':visible')) {
            e.preventDefault();
            alert('Please choose a different username.');
        }
    });
});