import flet as ft
import google.generativeai as genai
from pypdf import PdfReader
import os
import asyncio
import hashlib
import uuid

# --- ⚠️ إعدادات الأمان ---
API_KEY = "YOUR_API_KEY_HERE"  # ضع مفتاحك هنا
SECRET_SALT = "MAMDOH_APP_2025_SECRET" # ⚠️ مفتاح التشفير السري (لا تغيره بعد إصدار التطبيق)

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"Error: {e}")

def main(page: ft.Page):
    page.title = "Smart Solver Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 390
    page.window_height = 844
    page.scroll = ft.ScrollMode.ADAPTIVE

    # --- نظام الحماية (Licensing System) ---
    
    def get_device_id():
        """يجلب أو ينشئ معرفاً فريداً للجهاز ويحفظه"""
        stored_id = page.client_storage.get("device_id")
        if not stored_id:
            stored_id = str(uuid.uuid4()).split('-')[0].upper()
            page.client_storage.set("device_id", stored_id)
        return stored_id

    def check_license_validity(entered_key):
        device_id = get_device_id()
        # معادلة التشفير
        expected_key = hashlib.sha256((device_id + SECRET_SALT).encode()).hexdigest()[:10].upper()
        return entered_key.strip().upper() == expected_key

    # --- شاشة القفل (مع بياناتك) ---
    
    def show_lock_screen():
        device_id = get_device_id()
        
        txt_id = ft.TextField(
            value=device_id, 
            label="معرف جهازك (Device ID)", 
            read_only=True, 
            text_align="center",
            bgcolor=ft.colors.GREY_100
        )
        
        txt_key = ft.TextField(
            label="أدخل مفتاح التفعيل هنا", 
            text_align="center",
            password=True,
            can_reveal_password=True,
            text_size=16
        )
        
        lbl_error = ft.Text("", color="red", weight="bold")

        def activate_click(e):
            if check_license_validity(txt_key.value):
                page.client_storage.set("license_key", txt_key.value)
                page.snack_bar = ft.SnackBar(ft.Text("✅ تم التفعيل بنجاح! أهلاً بك."))
                page.snack_bar.open = True
                page.update()
                page.clean()
                run_app_logic()
            else:
                lbl_error.value = "❌ مفتاح خاطئ! تأكد من الكود."
                page.update()

        # تصميم شاشة القفل
        page.add(
            ft.Column(
                [
                    ft.Icon(ft.icons.SECURITY, size=60, color="indigo"),
                    ft.Text("Smart Solver Pro 🔒", size=24, weight="bold", color="indigo"),
                    ft.Divider(),
                    
                    ft.Text("هذا البرنامج مدفوع ومحمي.", size=16),
                    ft.Text("لشراء مفتاح التفعيل، تواصل مع:", size=14),
                    
                    # 👇 هنا تظهر بياناتك بوضوح
                    ft.Container(
                        content=ft.Column([
                            ft.Text("المهندس ممدوح", size=18, weight="bold", color="blue"),
                            ft.Text("📞 01026787011", size=18, weight="bold", color="blue"),
                        ], horizontal_alignment="center"),
                        bgcolor=ft.colors.BLUE_50,
                        padding=10,
                        border_radius=10
                    ),
                    
                    ft.Divider(),
                    ft.Text("1. انسخ معرف جهازك:", size=12),
                    txt_id,
                    ft.ElevatedButton("نسخ المعرف", icon=ft.icons.COPY, 
                                      on_click=lambda _: page.set_clipboard(device_id)),
                    
                    ft.Text("2. أرسله للمهندس واستلم المفتاح:", size=12),
                    txt_key,
                    lbl_error,
                    ft.ElevatedButton("تفعيل الدخول", on_click=activate_click, 
                                      bgcolor="green", color="white", width=200, height=50)
                ],
                horizontal_alignment="center",
                alignment="center",
                spacing=15,
                scroll=ft.ScrollMode.ADAPTIVE
            )
        )

    # --- منطق التطبيق الأساسي ---
    
    def run_app_logic():
        img_picker = ft.FilePicker()
        page.overlay.append(img_picker) 

        TARGET_BOOK_NAME = "book.pdf"
        book_text_content = ""

        status_txt = ft.Text("جاري تشغيل النظام...", size=16, color="blue", text_align="center")
        result_area = ft.Markdown(selectable=True)
        loading_bar = ft.ProgressBar(width=200, visible=False)
        
        btn_scan = ft.FilledButton(
            "📸 اضغط لتصوير السؤال", 
            icon="camera_alt",
            visible=False,
            width=300, height=60,
            style=ft.ButtonStyle(bgcolor="blue", color="white")
        )

        async def solve_question(image_path):
            loading_bar.visible = True
            status_txt.value = "🧐 جاري تحليل السؤال والبحث في الكتاب..."
            status_txt.color = "orange"
            btn_scan.visible = False
            page.update()

            try:
                myfile = genai.upload_file(image_path)
                prompt = f"""
                Instructions:
                Answer using ONLY the book content below.
                If not found, say "الإجابة غير موجودة في الكتاب".
                --- Book Content ---
                {book_text_content} 
                Question: Solve the question in the image.
                """
                response = await model.generate_content_async([prompt, myfile])
                result_area.value = response.text
                status_txt.value = "✅ تم الحل."
                status_txt.color = "green"
            except Exception as ex:
                result_area.value = f"Error: {ex}"
                status_txt.value = "خطأ"
                status_txt.color = "red"

            loading_bar.visible = False
            btn_scan.text = "📸 سؤال جديد"
            btn_scan.visible = True
            page.update()

        async def on_img_picked(e):
            if e.files:
                await solve_question(e.files[0].path)

        async def start_sequence(e=None):
            nonlocal book_text_content
            await asyncio.sleep(1)
            status_txt.value = "📂 جاري تحميل الكتاب..."
            page.update()
            
            if not os.path.exists(TARGET_BOOK_NAME):
                status_txt.value = "❌ الكتاب غير موجود!"
                return

            try:
                reader = PdfReader(TARGET_BOOK_NAME)
                text = ""
                # قراءة الكتاب كاملاً
                for i in range(len(reader.pages)):
                    text += reader.pages[i].extract_text() + "\n"
                    if i % 50 == 0:
                        status_txt.value = f"📂 تمت قراءة {i} صفحة..."
                        page.update()

                book_text_content = text
                status_txt.value = "✅ البرنامج جاهز للعمل."
                status_txt.color = "green"
                btn_scan.visible = True
                page.update()
            except Exception as ex:
                status_txt.value = f"Error: {ex}"
                page.update()

        img_picker.on_result = on_img_picked
        btn_scan.on_click = lambda _: img_picker.pick_files(file_type=ft.FilePickerFileType.IMAGE)

        page.add(
            ft.Column(
                [
                    ft.Text("Smart Solver Pro 🚀", size=28, weight="bold", color="indigo"),
                    status_txt,
                    loading_bar,
                    ft.Divider(),
                    btn_scan,
                    ft.Divider(),
                    ft.Container(result_area, bgcolor=ft.colors.GREY_100, padding=10, border_radius=10, expand=True),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            )
        )
        page.run_task(start_sequence)

    # نقطة البداية
    saved_key = page.client_storage.get("license_key")
    if saved_key and check_license_validity(saved_key):
        run_app_logic()
    else:
        show_lock_screen()

ft.app(target=main)