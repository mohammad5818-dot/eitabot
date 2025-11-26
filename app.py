<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <title>ویرایشگر هوشمند عکس</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- TailwindCSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://bot.eitaa.com/eitaa-web-app.js"></script>
</head>
<body class="bg-gray-100 text-gray-800 font-sans rtl">

    <div class="max-w-md mx-auto p-4">

        <!-- عنوان -->
        <h2 class="text-2xl font-bold mb-4 text-center">ویرایشگر هوشمند عکس</h2>

        <!-- وضعیت کاربر -->
        <div id="app-status" class="p-3 rounded mb-4 bg-yellow-100 text-yellow-800">
            در حال بررسی وضعیت و عضویت شما...
        </div>

        <!-- فرم اصلی -->
        <div id="main-form" class="space-y-4 hidden">

            <p id="credit-display" class="text-center font-semibold">اعتبار باقی‌مانده: **0**</p>

            <div>
                <label class="block mb-1 font-medium">۱. ارسال عکس:</label>
                <input type="file" id="image-file" accept="image/jpeg, image/png" 
                       class="w-full p-2 border rounded border-gray-300 bg-white" required>
            </div>

            <div>
                <label class="block mb-1 font-medium">۲. پرامپت (دستور ویرایش):</label>
                <textarea id="prompt-text" placeholder="مثال: «این شخص را با عینک آفتابی و پس‌زمینه ساحلی نشان بده.»" 
                          class="w-full p-2 border rounded border-gray-300 resize-y" required></textarea>
            </div>

            <button id="process-btn" class="w-full bg-green-500 text-white py-2 rounded font-bold hover:bg-green-600 transition">
                🔄 شروع ویرایش عکس
            </button>
        </div>

        <!-- منوی خرید اعتبار -->
        <div id="credit-menu" class="hidden text-center space-y-2">
            <p class="text-red-700 font-semibold">اعتبار شما به پایان رسیده است.</p>
            <div class="flex justify-between gap-2">
                <button onclick="buyCredit(10)" class="flex-1 bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition">+۱۰ عکس (۵۰ تومان)</button>
                <button onclick="buyCredit(20)" class="flex-1 bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition">+۲۰ عکس (۹۰ تومان)</button>
            </div>
        </div>

        <!-- خروجی -->
        <div id="output-area" class="mt-4 hidden">
            <h4 class="font-bold mb-2">✅ نتیجه ویرایش:</h4>
            <pre id="output-text" class="p-3 bg-green-100 text-green-800 rounded"></pre>
        </div>

        <!-- دکمه بستن برنامک -->
        <button onclick="Eitaa.WebApp.close()" 
                class="w-full mt-4 bg-gray-200 text-gray-800 py-2 rounded hover:bg-gray-300 transition">
            ❌ بستن برنامک
        </button>

    </div>

    <script>
        let userId;

        // بررسی محیط ایتا
        if (window.Eitaa?.WebApp?.initDataUnsafe?.user) {
            Eitaa.WebApp.ready();
            userId = Eitaa.WebApp.initDataUnsafe.user.id;
            checkStatus();
        } else {
            const statusDiv = document.getElementById('app-status');
            statusDiv.className = 'p-3 rounded mb-4 bg-red-100 text-red-800';
            statusDiv.innerText = '❌ خطای راه‌اندازی: لطفاً این صفحه را از طریق ربات ایتا باز کنید.';
        }

        // بررسی وضعیت عضویت و اعتبار
        async function checkStatus() {
            try {
                const response = await fetch('/api/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId })
                });
                const data = await response.json();

                const statusDiv = document.getElementById('app-status');
                const creditDisplay = document.getElementById('credit-display');

                if (data.is_member) {
                    statusDiv.className = 'p-3 rounded mb-4 bg-green-100 text-green-800';
                    statusDiv.innerHTML = '✅ عضویت شما تایید شد. خوش آمدید!';
                    creditDisplay.innerHTML = `اعتبار باقی‌مانده: **${data.credits}** عکس`;

                    document.getElementById('main-form').classList.toggle('hidden', data.credits <= 0);
                    document.getElementById('credit-menu').classList.toggle('hidden', data.credits > 0);

                } else {
                    statusDiv.className = 'p-3 rounded mb-4 bg-red-100 text-red-800';
                    statusDiv.innerHTML = `
                        ❌ برای استفاده از برنامک، لطفاً در کانال‌های زیر عضو شوید:<br>
                        ${data.required_channels.map(c => `<a href="https://t.me/${c}" target="_blank">@${c}</a>`).join(', ')}
                        <br>بعد از عضویت، برنامک را مجدداً باز کنید.
                    `;
                    document.getElementById('main-form').classList.add('hidden');
                    document.getElementById('credit-menu').classList.add('hidden');
                }
            } catch {
                const statusDiv = document.getElementById('app-status');
                statusDiv.className = 'p-3 rounded mb-4 bg-red-100 text-red-800';
                statusDiv.innerText = '❌ خطای ارتباط با سرور.';
            }
        }

        // پردازش عکس
        document.getElementById('process-btn').addEventListener('click', processImage);

        async function processImage() {
            const fileInput = document.getElementById('image-file');
            const promptText = document.getElementById('prompt-text').value;
            const processBtn = document.getElementById('process-btn');

            if (!fileInput.files.length || !promptText) {
                alert('لطفاً عکس و پرامپت را وارد کنید.');
                return;
            }

            processBtn.disabled = true;
            processBtn.innerText = '... در حال پردازش توسط Gemini';
            document.getElementById('output-area').classList.add('hidden');

            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Image = reader.result;
                try {
                    const response = await fetch('/api/process_image', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, image: base64Image, prompt: promptText })
                    });
                    const data = await response.json();

                    if (data.status === 'success') {
                        document.getElementById('output-text').innerText = data.result;
                        document.getElementById('output-area').classList.remove('hidden');
                        document.getElementById('credit-display').innerHTML = `اعتبار باقی‌مانده: **${data.remaining_credits}** عکس`;

                        Eitaa.WebApp.sendData(JSON.stringify({ result: 'success', prompt: promptText }));
                    } else {
                        alert(`خطا: ${data.message || 'خطای ناشناخته.'}`);
                    }

                } catch {
                    alert('خطا در ارسال به سرور.');
                } finally {
                    processBtn.disabled = false;
                    processBtn.innerText = '🔄 شروع ویرایش عکس';
                    checkStatus();
                }
            };
            reader.readAsDataURL(fileInput.files[0]);
        }

        // خرید اعتبار
        async function buyCredit(amount) {
            const creditMenu = document.getElementById('credit-menu');
            creditMenu.innerHTML = 'در حال انتقال به صفحه پرداخت... (این یک شبیه‌سازی است)';

            try {
                const response = await fetch('/api/buy_credit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, amount })
                });
                const data = await response.json();
                alert(`تبریک! شما ${amount} اعتبار خریدید. اعتبار جدید: ${data.new_credits}`);
            } catch {
                alert('خطا در خرید اعتبار.');
            } finally {
                checkStatus();
            }
        }
    </script>

</body>
</html>
