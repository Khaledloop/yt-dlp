import sys
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # واجهة المستخدم
        html = """
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>YT-DLP Official Source</title>
            <style>
                body { font-family: sans-serif; background: #111; color: #fff; text-align: center; padding: 20px; }
                input { padding: 10px; width: 80%; border-radius: 5px; border: none; }
                button { padding: 10px 20px; background: red; color: white; border: none; cursor: pointer; font-weight: bold; }
                textarea { width: 90%; height: 300px; margin-top: 20px; background: #222; color: #0f0; border: 1px solid #444; }
            </style>
        </head>
        <body>
            <h2>مستخرج YT-DLP (من المصدر الرسمي) 📦</h2>
            <form method="POST">
                <input type="text" name="url" placeholder="ضع الرابط..." required>
                <button type="submit">استخراج</button>
            </form>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            data = self.rfile.read(length).decode('utf-8')
            url = urllib.parse.parse_qs(data).get('url', [''])[0]
        except: url = ""

        result_text = ""
        
        if url:
            # هنا السحر: بنشغل الأداة من ملفاتها الأصلية مباشرة
            # -m yt_dlp: بتشغل الباكدج اللي انت حملتها
            command = [
                sys.executable, "-m", "yt_dlp",
                "--dump-json",
                "--no-check-certificate", # ضروري عشان SSL في Wasmer
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang", "ar,en",
                url
            ]
            
            try:
                # تنفيذ الأمر
                output = subprocess.check_output(command, stderr=subprocess.STDOUT)
                data = json.loads(output.decode('utf-8'))
                
                # البحث عن الترجمة
                transcript_url = None
                
                # دالة مساعدة للبحث في JSON
                def find_sub(subs_dict):
                    for lang in ['ar', 'en']:
                        if lang in subs_dict:
                            for fmt in subs_dict[lang]:
                                if fmt.get('ext') == 'json3':
                                    return fmt['url']
                    return None

                transcript_url = find_sub(data.get('subtitles', {}))
                if not transcript_url:
                    transcript_url = find_sub(data.get('automatic_captions', {}))
                
                if transcript_url:
                    # تحميل النص بـ Curl لأن بايثون فيه مشاكل SSL
                    transcript_text = subprocess.check_output(["curl", "-k", "-s", transcript_url]).decode('utf-8')
                    
                    # تنظيف النص
                    events = json.loads(transcript_text).get('events', [])
                    lines = []
                    for event in events:
                        if 'segs' in event:
                            for seg in event['segs']:
                                if 'utf8' in seg: lines.append(seg['utf8'])
                    
                    result_text = " ".join(lines)
                else:
                    result_text = "لم يتم العثور على ترجمة (JSON3)."

            except Exception as e:
                # لو حصل خطأ نعرضه زي ما هو عشان نفهم
                error_msg = str(e)
                if hasattr(e, 'output'):
                    error_msg += "\nOutput: " + e.output.decode('utf-8', errors='ignore')
                result_text = f"خطأ: {error_msg}"

        # عرض النتيجة
        response_html = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head><meta charset="UTF-8"><title>النتيجة</title></head>
        <body style="background:#111; color:#fff; text-align:center;">
            <h3>النتيجة:</h3>
            <textarea style="width:90%; height:400px; background:#222; color:#fff;">{result_text}</textarea>
            <br><br>
            <a href="/" style="color:yellow;">عودة</a>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(response_html.encode('utf-8'))

if __name__ == "__main__":
    # تشغيل السيرفر
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, Handler)
    print("YT-DLP Source Server Started...")
    httpd.serve_forever()
