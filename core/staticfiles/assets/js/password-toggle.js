// گرفتن تمام دکمه‌های تاگل در صفحه
const toggleButtons = document.querySelectorAll('.toggle-btn');

toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
        // پیدا کردن اینپوت و آیکونِ دقیقاً همون بلوکی که روش کلیک شده
        const input = this.parentElement.querySelector('.pass-input');
        const icon = this.querySelector('i');

        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.replace('bi-eye-slash', 'bi-eye');
        } else {
            input.type = 'password';
            icon.classList.replace('bi-eye', 'bi-eye-slash');
        }
    });
});
