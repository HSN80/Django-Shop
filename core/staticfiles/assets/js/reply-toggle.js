// const reply = document.getElementById('reply')

// reply.addEventListener('click',function(e) {
//     if (e.target !== this) return;
//     const csrf_token = document.querySelector('[name=csrfmiddlewaretoken]').value;
//     if (!reply.querySelector('form')){
//         const form = document.createElement('form');
//         form.className = 'mt2';
//         form.method = 'POST';
//         form.action = '{% url "products:Comment_create"  %}';

//         form.innerHTML = `
//             {% csrf_token %}
//             <div class="mb-2">
//                 <textarea name="body" class="form-control" placeholder="reply" rows="3" required></textarea>
//             </div>
//             <div class="d-flex gap-2">
//                 <button type="submit" class="btn review-cta">send</button>
//             </div>
//         `;
//         reply.appendChild(form);
//     }
// });


// document.addEventListener('DOMContentLoaded', function() {
//     // پیدا کردن تمام دکمه‌های ریپلی در صفحه
//     const replyButtons = document.querySelectorAll('.reply-btn');
    
//     // گرفتن توکن CSRF از فرم کامنت اصلی که در بالای صفحه قرار دارد
//     const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

//     replyButtons.forEach(button => {
//         button.addEventListener('click', function(e) {
//             e.preventDefault();

//             // پیدا کردن دایو دربرگیرنده دکمه‌ها (entry-actions)
//             const actionsDiv = this.parentElement;
            
//             // گرفتن آیدی کامنتی که می‌خواهیم به آن جواب دهیم
//             const commentId = this.getAttribute('data-comment-id');

//             // بررسی اینکه آیا فرم ریپلی از قبل زیر این کامنت باز شده است یا نه
//             let existingForm = actionsDiv.nextElementSibling;
//             if (existingForm && existingForm.classList.contains('dynamic-reply-form')) {
//                 // اگر فرم باز بود، با کلیک مجدد بسته شود
//                 existingForm.remove();
//                 return;
//             }

//             // (اختیاری) بستن سایر فرم‌های ریپلی باز شده در صفحه
//             document.querySelectorAll('.dynamic-reply-form').forEach(f => f.remove());

//             // ساخت یک نگهدارنده برای فرم
//             const formContainer = document.createElement('div');
//             formContainer.className = 'dynamic-reply-form mt-3 mb-3';

//             // کدهای HTML فرم ریپلی (دقت کنید که از علامت ` استفاده شده است)
//             formContainer.innerHTML = `
//                 <form action="{% url 'products:Comment_create' %}" method="post" class="p-3 border rounded bg-light">
//                     <!-- فیلد مخفی برای CSRF Token -->
//                     <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                    
//                     <!-- فیلد مخفی برای ارسال آیدی کامنت والد (برای جنگو) -->
//                     <input type="hidden" name="parent_id" value="${commentId}">
                    
//                     <div class="mb-2">
//                         <textarea name="body" class="form-control" placeholder="Write your reply..." rows="3" required></textarea>
//                     </div>
//                     <div class="d-flex gap-2">
//                         <button type="submit" class="btn btn-primary btn-sm">Send Reply</button>
//                         <button type="button" class="btn btn-secondary btn-sm cancel-reply">Cancel</button>
//                     </div>
//                 </form>
//             `;

//             // اضافه کردن فرم دقیقاً بعد از دکمه‌های لایک و ریپلی
//             actionsDiv.insertAdjacentElement('afterend', formContainer);

//             // فعال‌سازی دکمه انصراف (Cancel) برای بستن فرم
//             formContainer.querySelector('.cancel-reply').addEventListener('click', function() {
//                 formContainer.remove();
//             });
//         });
//     });
// });

document.addEventListener('DOMContentLoaded', function () {
    const replyButtons = document.querySelectorAll('.reply-btn');

    replyButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();

            const parentArticle = this.closest('.review-entry');
            const commentId = this.dataset.commentId;
            const actionUrl = this.dataset.url;

            // دریافت توکن CSRF از فرم اصلی موجود در صفحه
            const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfToken = csrfInput ? csrfInput.value : '';

            // بررسی وجود فرم باز در این کامنت (برای Toggle شدن)
            let existingForm = parentArticle.querySelector('.dynamic-reply-wrapper');
            if (existingForm) {
                existingForm.remove();
                return;
            }

            // بستن تمام فرم‌های ریپلی باز در سایر کامنت‌ها
            document.querySelectorAll('.dynamic-reply-wrapper').forEach(form => form.remove());

            // ساخت کانتینر فرم با کلاس reply-entry برای حفظ ساختار درختی و تورفتگی
            const formContainer = document.createElement('div');
            formContainer.className = 'review-entry reply-entry dynamic-reply-wrapper mt-3';

            // HTML فرم با استایل‌های هماهنگ با قالب
            formContainer.innerHTML = `
                <form action="${actionUrl}" method="post" class="w-100">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                    <input type="hidden" name="parent" value="${commentId}">
                    
                    <div class="mb-3">
                        <textarea name="body" class="form-control" placeholder="Write your reply..." rows="3" required></textarea>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn review-cta">Send Reply</button>
                        <button type="button" class="btn btn-outline-secondary cancel-reply-btn">Cancel</button>
                    </div>
                </form>
            `;

            // قرار دادن فرم در جای مناسب (بین دکمه‌ها و پاسخ‌های قبلی)
            const actionsDiv = parentArticle.querySelector('.entry-actions');
            actionsDiv.insertAdjacentElement('afterend', formContainer);

            // فوکوس خودکار روی کادر متن
            formContainer.querySelector('textarea').focus();

            // عملکرد دکمه انصراف
            formContainer.querySelector('.cancel-reply-btn').addEventListener('click', function () {
                formContainer.remove();
            });
        });
    });
});
