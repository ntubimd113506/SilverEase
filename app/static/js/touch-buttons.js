document.addEventListener('DOMContentLoaded', function () {
    var buttons = document.querySelectorAll('.btn, input[type="submit"], .delete-btn, input.delete_confirm, .submit-button, #myButton, input[type="submit" i]');

    buttons.forEach(function (button) {
        button.addEventListener('touchstart', function () {
            button.classList.add('active');
        });

        button.addEventListener('touchend', function () {
            setTimeout(function () {
                button.classList.remove('active');
            }, 100);
        });

        button.addEventListener('click', function () {
            setTimeout(function () {
                button.classList.remove('active');
            }, 100);
        });
    });
});
