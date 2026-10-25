# CodeHarness

دستیار برنامه‌نویسی محلی برای ویندوز که روی رایانهٔ خودتان اجرا می‌شود و پیش از دست‌زدن به هر چیزی اجازه می‌گیرد. رابط پیش‌فرض فارسی (راست‌به‌چپ) است و انگلیسی با یک سوئیچ در دسترس.

یک مدل نمایشی آفلاین همراه برنامه است تا پیش از آنکه کلید داشته باشید، یک فراخوانی واقعی ابزار و یک پاسخ واقعی ببینید.

<p align="center">
  <img src="docs/screenshots/run.png" alt="یک اجرای واقعی با مدل نمایشی" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۱.</strong> یک اجرای واقعی با مدل نمایشی: خط ابزار <code>read_file</code>، پاسخ مدل با نقل‌قول از فایل، و شمارندهٔ توکن.</p>

همهٔ تصاویر زیر از برنامهٔ نصب‌شده (`CodeHarness-Setup-0.1.0.exe`) گرفته شده‌اند، به فارسی و در اندازهٔ مرجع. روش تهیهٔ هر تصویر و تفاوت‌های ساخت با ماکت‌های طراحی در [`docs/screenshots/README.md`](docs/screenshots/README.md) آمده است.

## نصب

1. `CodeHarness-Setup-0.1.0.exe` را دانلود کنید (یا `CodeHarness-0.1.0-x64.zip` را برای نسخهٔ قابل‌حمل بردارید — هرجا باز کنید و `CodeHarness.exe` را اجرا کنید).
2. اجرایش کنید. ویندوز پیام **«Windows protected your PC»** را نشان می‌دهد، چون نصب‌کننده امضای کد ندارد. روی **More info** و سپس **Run anyway** بزنید.
3. یک پوشه انتخاب کنید — مسیر پیش‌فرضِ هر کاربر است و به دسترسی مدیر نیاز ندارد — و نصب را تمام کنید.

هیچ چیز دیگری لازم نیست: **نه پایتون، نه نود، نه ابزار ساخت.** موتور داخل برنامه است و نصب‌کننده آن را همان‌جا می‌گذارد.

## اولین اجرا

1. یک پوشهٔ پروژه انتخاب کنید، یا روی **پروژهٔ نمونه** بزنید تا نمونهٔ همراه برنامه باز شود. این نمونه یک مهارت پروژه‌ای (`read-framework-docs`) دارد که خاموش شروع می‌شود، چون مهارت پروژه باید یک انتخاب آگاهانه باشد.
2. مدل را روی **نمایشی** بگذارید. آفلاین پاسخ می‌دهد و همان ابزارهایی را صدا می‌زند که یک مدل واقعی صدا می‌زند.
3. بنویسید: `read README.md and summarize`. باید یک خط ابزار ببینید و بعد پاسخی که از فایل خودتان نقل‌قول می‌کند.

<p align="center">
  <img src="docs/screenshots/home.png" alt="صفحهٔ نخست در اولین اجرا" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۲.</strong> اولین اجرا: نه پوشه‌ای انتخاب شده و نه مدلی؛ دو کارت خالی راه را نشان می‌دهند و مدل نمایشی با یک کلیک آماده است.</p>

<p align="center">
  <img src="docs/screenshots/main.png" alt="صفحهٔ کار آماده برای نوشتن" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۳.</strong> صفحهٔ کار با فضای کاری نمونه و مدل نمایشی؛ نوار پایین: انتخاب فضا، شاخه، Worktree، حالت اجازه و مدل.</p>

## فضای کاری

عامل داخل یک پوشه کار می‌کند. این نما همان پوشه‌ای است که او می‌بیند: درخت فایل‌ها، پیش‌نمایش فایل، و کارهایی که در این فضا اجرا شده‌اند. فایلی را که عامل تغییر داده می‌توانید از همین‌جا بایت‌به‌بایت برگردانید.

<p align="center">
  <img src="docs/screenshots/workspace.png" alt="مرورگر فضای کاری" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۴.</strong> مرورگر فضای کاری: درخت فایل‌ها، پیش‌نمایش README نمونه و کارهایی که در این فضا اجرا شده‌اند.</p>

## تأییدها و امتناع‌ها

در حالت **با تأیید**، عامل پیش از هر نوشتن می‌ایستد و منتظر می‌ماند. صندوق تأیید همان رکوردهایی را دارد که اجرا دارد؛ تصمیم‌گرفتن در آن، اجرا را ادامه می‌دهد. درخواست چیزی بیرون از پوشه اصلاً سؤال تأیید نیست — لایهٔ ابزار آن را رد می‌کند و اجرا با همان رد در تاریخچه‌اش ادامه پیدا می‌کند.

<p align="center">
  <img src="docs/screenshots/inbox.png" alt="یک درخواست در انتظار تصمیم" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۵.</strong> یک درخواست واقعی در انتظار تصمیم: تغییر پیشنهادی فایل با diff، سطح ریسک و دکمه‌های تأیید، ویرایش و رد.</p>

<p align="center">
  <img src="docs/screenshots/inbox-empty.png" alt="صندوق تأیید خالی" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۶.</strong> صندوق تأیید وقتی چیزی منتظر تصمیم نیست؛ عامل هم تا تصمیم شما نمی‌گذرد.</p>

<p align="center">
  <img src="docs/screenshots/errors.png" alt="کارت امتناع" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۷.</strong> کارت امتناع: مسیری بیرون از فضای کاری، حتی با تأیید هم خوانده نمی‌شود.</p>

## افزودن مدل

تنظیمات › مدل‌ها › **افزودن**. یک پیش‌تنظیم انتخاب کنید (یا نشانی پایه را بنویسید)، کلید را بچسبانید و **آزمایش** را بزنید. کلیدها با API حفاظت دادهٔ ویندوز (DPAPI) در فایل `vault.json` داده‌های کاربرِ برنامه رمز می‌شوند؛ موتور آن‌ها را در حافظه می‌گیرد و هیچ‌جا نمی‌نویسد. ویرایش یک مدل با کلید خالی، کلید قبلی را نگه می‌دارد. دکمهٔ آزمایش تنها چیزی است که پیش از اجرای یک کار با ارائه‌دهنده حرف می‌زند.

<p align="center">
  <img src="docs/screenshots/settings.png" alt="تنظیمات، مدل‌ها و کلیدها" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۸.</strong> تنظیمات › مدل‌ها و کلیدها: مدل نمایشی همیشه در دسترس است و کلیدها فقط روی همین دستگاه می‌مانند.</p>

<p align="center">
  <img src="docs/screenshots/settings-add-model.png" alt="افزودن مدل" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۹.</strong> افزودن مدل: پیش‌تنظیم‌ها، نشانی پایه، کلید و دکمهٔ آزمایش اتصال.</p>

## افزودن مهارت

سفارشی‌سازی › مهارت‌ها. مهارت یک پوشه با فایل `SKILL.md` است؛ برای همهٔ پروژه‌ها آن را در `%APPDATA%\CodeHarness\skills\` بگذارید، یا برای یک پروژه در `<your project>\.harness\skills\`. مهارت‌ها در هر پرامپت چسبانده نمی‌شوند: مدل نامشان را می‌بیند و وقتی لازم داشت با `load_skill` بدنه را می‌خواهد، و خط زمان نشان می‌دهد این کار چه وقت رخ داد.

<p align="center">
  <img src="docs/screenshots/skills.png" alt="سفارشی‌سازی، مهارت‌ها" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۱۰.</strong> سفارشی‌سازی › مهارت‌ها: مهارت پروژهٔ نمونه شمرده شده ولی روشن نیست — شمارنده می‌گوید ۱ مهارت، ۰ فعال، ۰ سرور؛ روشن‌کردن، یک تصمیم آگاهانه است.</p>

## افزودن زمان‌بندی

زمان‌بندی › **جدید**. یک زمان‌بندی، یک درخواست ذخیره‌شده به‌همراه تکرار است. فقط وقتی برنامه باز است اجرا می‌شود — این قاعدهٔ محصول است، نه محدودیت. نوبتی که در زمان بسته‌بودن برنامه رسیده باشد، دفعهٔ بعد که برنامه را باز می‌کنید **پیشنهاد** می‌شود؛ هیچ چیز خودبه‌خود شروع نمی‌شود. سقف مجوز بخشی از خود زمان‌بندی است و اجرای بدون‌ناظر به‌طور پیش‌فرض فقط‌خواندنی و با گزارش است.

<p align="center">
  <img src="docs/screenshots/schedule.png" alt="زمان‌بندی" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۱۱.</strong> زمان‌بندی: یک زمان‌بندی هفتگی واقعی با اجرای بعدی، حالت اجرا و سقف مجوز؛ پایین‌تر، الگوهای آماده برای شروع.</p>

<p align="center">
  <img src="docs/screenshots/schedule-add.png" alt="افزودن زمان‌بندی" width="880">
</p>
<p align="center" dir="rtl"><strong>تصویر ۱۲.</strong> افزودن زمان‌بندی از یک الگوی آماده: نام، درخواست، تکرار هفتگی، ساعت و سقف مجوز؛ حالت اجرای مؤثر زیر همان انتخاب نوشته می‌شود.</p>

## بقیهٔ تنظیمات

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/settings-appearance.png" alt="ظاهر و زبان"></td>
    <td width="50%"><img src="docs/screenshots/settings-permissions.png" alt="مجوزها و ایمنی"></td>
  </tr>
  <tr>
    <td align="center" dir="rtl"><strong>تصویر ۱۳.</strong> ظاهر و زبان: زبان رابط، تم، اندازهٔ قلم و نمایش فعالیت عامل.</td>
    <td align="center" dir="rtl"><strong>تصویر ۱۴.</strong> مجوزها و ایمنی: حالت پیش‌فرض اجازه، شرط‌هایی که همیشه می‌پرسند و قواعد مجاز.</td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/settings-context.png" alt="زمینه و فشرده‌سازی"></td>
    <td><img src="docs/screenshots/settings-terminal.png" alt="ترمینال و آزمون‌ها"></td>
  </tr>
  <tr>
    <td align="center" dir="rtl"><strong>تصویر ۱۵.</strong> زمینه و فشرده‌سازی: اندازهٔ پنجرهٔ زمینه، آستانهٔ فشرده‌سازی و مقدار نگهداری.</td>
    <td align="center" dir="rtl"><strong>تصویر ۱۶.</strong> ترمینال و آزمون‌ها: پوستهٔ دستور، مهلت اجرا و تشخیص آزمون‌ها.</td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/settings-data.png" alt="داده‌ها و حریم خصوصی"></td>
    <td><img src="docs/screenshots/settings-about.png" alt="درباره"></td>
  </tr>
  <tr>
    <td align="center" dir="rtl"><strong>تصویر ۱۷.</strong> داده‌ها و حریم خصوصی: محل داده‌ها، مسیر پروژه و مدت نگهداری تاریخچه؛ پاک‌کردن همهٔ کلیدها.</td>
    <td align="center" dir="rtl"><strong>تصویر ۱۸.</strong> درباره: نسخه، مجوز و محدودیت‌ها.</td>
  </tr>
</table>

## معماری

```
┌────────────────────────────────────────────────────────────┐
│ CodeHarness.exe  (Electron)                                │
│  ├─ renderer: the Next.js export, over app://codeharness   │
│  └─ main: spawns the watchdog, holds the per-launch token  │
└───────────────────────────┬────────────────────────────────┘
                            │ stdin: {"token", "app_data"}
                  ┌─────────▼─────────┐
                  │ watchdog.exe      │  kill-on-close job
                  └─────────┬─────────┘
                            │
                  ┌─────────▼──────────────────────────────┐
                  │ engine.exe (PyInstaller onedir)        │
                  │  FastAPI on 127.0.0.1:<random port>    │
                  │  bearer token required on every route  │
                  │  ├─ agent: deepagents + LangGraph      │
                  │  ├─ tools: jail, files, commands, git  │
                  │  └─ permissions: modes, rules, approval│
                  └────────────────────────────────────────┘
```

توکن در هر اجرا ساخته می‌شود، در فرایند اصلی الکترون می‌ماند و هر مسیر — از جمله `/health` — آن را می‌خواهد. موتور فقط روی loopback گوش می‌دهد. بستن پنجره، job نگهبان را تمام می‌کند و آن هم موتور و هر چیزی را که موتور شروع کرده پایان می‌دهد.

موتور جدا از برنامه هم از `backend/` با `python -m server` و یک توکن روی stdin اجرا می‌شود؛ `python -m server --dev` احراز هویت را برای توسعهٔ محلی خاموش می‌کند. هر دو روی `127.0.0.1` با پورتی که سیستم‌عامل می‌دهد گوش می‌دهند.

## مجموعهٔ ارزیابی

```powershell
cd backend
uv run --project . python -m evals
```

بیست مورد قطعی از دل موتور واقعی — فرار از جیل، دستورهای پرخطر، دروازهٔ برنامه، دروازهٔ بازبینی، سقف حلقهٔ اصلاح، تأییدها، قواعد مجاز، افشای مهارت، پرسش‌ها، خرابی و ادامه، یک اجرای بدون‌ناظرِ فقط‌خواندنی، و یک بار دادهٔ معیوبِ رابط. گزارش را در `backend/evals/report.md` می‌نویسد و با شکست، خروجی غیرصفر می‌دهد. مدل‌های زنده یک چک‌لیست نوشته‌شده‌اند (`backend/evals/live-checklist.md`)، نه تستی که رد شده باشد و ادعای پوشش کند.

## بررسی‌ها

```powershell
cd backend; uv run --project . ruff check . ../scripts
uv run --project backend mypy --strict backend
npm run test:engine        # آزمون‌های موتور با pytest
npm run typecheck          # بررسی نوع‌ها با tsc
npm run test:ui            # قراردادهای تم، CSS منطقی و i18n
npm run build; npm run build:electron
npm run test:desktop       # Playwright روی نسخهٔ کاری
npm run desktop:build      # خروجی + الکترون + موتور PyInstaller
npm run package            # نصب‌کنندهٔ NSIS و zip قابل‌حمل در dist/
uv run --project backend python scripts/smoke-installer.py dist/win-unpacked
npx tsx tests/phase10-desktop.ts
npx tsx tests/phase10-screens.ts   # تصاویر بالا
```

تست‌های موتور را پیش از تست‌های رابط اجرا کنید: یک لاگ رویداد واقعی برای تست بازپخش می‌سازند. مسیرهای دسکتاپ برنامهٔ واقعی را می‌رانند و تصویرها و شواهد پاک‌سازی‌شده را در `artifacts/` (که در گیت نادیده گرفته می‌شود) ذخیره می‌کنند. تست‌های symlink به Developer Mode ویندوز یا دسترسی ساخت symlink نیاز دارند؛ خودِ بررسی containment هرگز رد نمی‌شود.

## محدودیت‌ها، صادقانه

پیش از اینکه این را به چیزی که برایتان مهم است وصل کنید، [`SECURITY.md`](SECURITY.md) را بخوانید. خلاصه‌اش: سندباکسی وجود ندارد. لایهٔ مجوز جلوی کارهایی را می‌گیرد که تأییدشان نکرده‌اید؛ جلوی برنامه‌ای را که تأیید کرده‌اید و بعد هر کاری می‌کند نمی‌گیرد. در پوشه‌ای کار کنید که بتوانید از کنترل نسخه برگردانید.

## توسعه

Node 24 و uv را نصب کنید، بعد:

```powershell
uv sync --project backend --frozen
npm ci
npm run generate:protocol
npm run generate:genui
npm run desktop          # خروجی، بسته‌بندی، اجرا
```

`npm run desktop:build` موتور PyInstaller را هم می‌سازد؛ `npm run package` نصب‌کننده را تولید می‌کند. `npm run icon` فایل `build/icon.ico` را از کد بازمی‌سازد، پس به ابزار طراحی نیاز نیست. مجوز MIT؛ طراحی با الهام از onboard-harness و بدون کپی کد از آن پروژهٔ AGPL.
