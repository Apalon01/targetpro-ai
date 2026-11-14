#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TargetPro AI — All-in-One Cloud Web Server & Telegram Bot Worker
Runs 24/7 on Render / Cloud VPS / Docker
"""
import os
import sys
import io
import time
import json
import gzip
import re
import base64
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import requests

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

PORT = int(os.environ.get("PORT", 8765))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDFS_DIR = os.path.join(BASE_DIR, "pdfs")
os.makedirs(PDFS_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(BASE_DIR, "tg-config.json")
MESSAGES_PATH = os.path.join(BASE_DIR, "tg-messages.json")
LEADS_PATH = os.path.join(BASE_DIR, "leads.txt")

def read_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_config():
    cfg = read_json(CONFIG_PATH)
    if not cfg:
        cfg = {
            "requireSub": True,
            "channelUsername": "@TargetPro_ai",
            "channelTitle": "TargetPro AI",
            "channelUrl": "https://t.me/TargetPro_ai",
            "instagramUsername": "@imamaliev.ads",
            "instagramUrl": "https://instagram.com/imamaliev.ads",
            "botToken": "9123687890:AAGiLeWOkWszeEt6S1vMLVZ6k1LRrDEGdFY",
            "publicAppUrl": "https://targetpro-ai.onrender.com"
        }
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    if render_url and not cfg.get("publicAppUrl"):
        cfg["publicAppUrl"] = render_url
    return cfg

def tg_api_call(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

def log_lead(text):
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LEADS_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {text}\n")
    except Exception:
        pass

# ==============================================================================
# HTTP REQUEST HANDLER
# ==============================================================================
class TargetProHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Health check for Render
        if path in ["/healthz", "/ping"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # 1. API: /api/tg-config
        if path == "/api/tg-config":
            cfg = get_config()
            public_cfg = {
                "requireSub": cfg.get("requireSub", True),
                "channelUsername": cfg.get("channelUsername", "@TargetPro_ai"),
                "channelTitle": cfg.get("channelTitle", "TargetPro AI"),
                "channelUrl": cfg.get("channelUrl", "https://t.me/TargetPro_ai"),
                "instagramUsername": cfg.get("instagramUsername", "@imamaliev.ads"),
                "instagramUrl": cfg.get("instagramUrl", "https://instagram.com/imamaliev.ads"),
                "publicAppUrl": cfg.get("publicAppUrl", "https://targetpro-ai.onrender.com")
            }
            body = json.dumps(public_cfg, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 2. API: /api/check-sub?user_id=...
        if path == "/api/check-sub":
            user_id = query.get("user_id", [""])[0].strip()
            cfg = get_config()
            token = cfg.get("botToken", "").strip()
            chan = cfg.get("channelUsername", "@TargetPro_ai").strip()

            is_subscribed = False
            if user_id and token:
                try:
                    url = f"https://api.telegram.org/bot{token}/getChatMember?chat_id={urllib.parse.quote(chan)}&user_id={urllib.parse.quote(user_id)}"
                    req = urllib.request.Request(url, headers={"User-Agent": "TargetPro-Checker"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("ok"):
                            status = data.get("result", {}).get("status", "")
                            if status in ["creator", "administrator", "member", "restricted"]:
                                is_subscribed = True
                except Exception:
                    is_subscribed = False
            elif not user_id:
                is_subscribed = True

            resp_obj = {
                "ok": True,
                "subscribed": is_subscribed,
                "channelUsername": chan,
                "channelUrl": cfg.get("channelUrl", "https://t.me/TargetPro_ai")
            }
            body = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 3. API: /api/insta?handle=...
        if path == "/api/insta":
            raw_input = query.get("handle", [""])[0].strip()
            clean_handle = raw_input
            m_post = re.search(r'instagram\.com/(?:[^/]+/)?(?:p|reel|tv)/([A-Za-z0-9_-]+)', raw_input)
            if m_post:
                try:
                    p_url = f"https://www.instagram.com/p/{m_post.group(1)}/embed/"
                    req = urllib.request.Request(p_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        m_owner = re.search(r'"username":"([A-Za-z0-9._]+)"', resp.read().decode("utf-8", "ignore"))
                        if m_owner:
                            clean_handle = m_owner.group(1)
                except Exception:
                    pass

            clean_handle = re.sub(r'^https?://(www\.)?instagram\.com/', '', clean_handle)
            clean_handle = re.split(r'[/?#]', clean_handle)[0].lstrip('@').strip()

            context_json = ""
            if clean_handle:
                log_lead(f"SCAN_INSTA: {clean_handle}")
                try:
                    embed_url = f"https://www.instagram.com/{clean_handle}/embed/"
                    req = urllib.request.Request(embed_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    })
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        html = resp.read().decode("utf-8", "ignore")
                        m_ctx = re.search(r'"contextJSON":"((?:\\.|[^"\\])*)"', html)
                        if m_ctx:
                            context_json = m_ctx.group(1).encode("utf-8").decode("unicode_escape")
                except Exception:
                    pass

            resp_obj = {
                "ok": True,
                "handle": clean_handle,
                "contextRaw": context_json,
                "ogTitle": "",
                "ogDescription": ""
            }
            body = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 4. Serve Generated PDFs: /pdfs/<filename>
        if path.startswith("/pdfs/"):
            pdf_filename = os.path.basename(path)
            pdf_filepath = os.path.join(PDFS_DIR, pdf_filename)
            if os.path.exists(pdf_filepath) and os.path.isfile(pdf_filepath):
                try:
                    with open(pdf_filepath, "rb") as f:
                        pdf_data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
                    self.send_cors_headers()
                    self.send_header("Content-Length", str(len(pdf_data)))
                    self.end_headers()
                    self.wfile.write(pdf_data)
                    return
                except Exception:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        # 5. Static Files (index.html, app-db.js, etc.)
        filename = "index.html" if path in ["/", ""] else path.lstrip("/")
        filepath = os.path.join(BASE_DIR, filename)

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            filepath = os.path.join(BASE_DIR, "index.html")

        content_type = "text/html; charset=utf-8"
        cache_ctrl = "no-cache"
        if filepath.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
            cache_ctrl = "public, max-age=86400"
        elif filepath.endswith(".css"):
            content_type = "text/css; charset=utf-8"
            cache_ctrl = "public, max-age=86400"
        elif filepath.endswith(".json"):
            content_type = "application/json; charset=utf-8"

        try:
            with open(filepath, "rb") as f:
                raw_bytes = f.read()

            accept_enc = self.headers.get("Accept-Encoding", "")
            if "gzip" in accept_enc:
                gz_bytes = gzip.compress(raw_bytes, 6)
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Cache-Control", cache_ctrl)
                self.send_cors_headers()
                self.send_header("Content-Length", str(len(gz_bytes)))
                self.end_headers()
                self.wfile.write(gz_bytes)
            else:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", cache_ctrl)
                self.send_cors_headers()
                self.send_header("Content-Length", str(len(raw_bytes)))
                self.end_headers()
                self.wfile.write(raw_bytes)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Server Error: {e}".encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/tg-config":
            self.send_response(403)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error":"Forbidden"}')
            return

        # 6. PDF Generation & Telegram Delivery
        if path == "/api/export-pdf":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8", "ignore")
            req_data = {}
            try:
                req_data = json.loads(post_body)
            except Exception:
                pass

            raw_handle = req_data.get("handle", "report")
            safe_handle = re.sub(r'[^A-Za-z0-9._-]', '', raw_handle) or "report"
            tg_user_id = str(req_data.get("tgUserId", "")).strip()
            pdf_base64 = req_data.get("pdfBase64", "")
            html_content = req_data.get("html", "")

            stamp_id = datetime.now().strftime("%H%M%S")
            file_name = f"TargetPro-AI-{safe_handle}-{stamp_id}.pdf"
            pdf_path = os.path.join(PDFS_DIR, file_name)

            pdf_bytes = None

            # Priority 1: High-fidelity client-rendered PDF bytes (perfect CSS/Grid/Fonts)
            if pdf_base64:
                try:
                    if "," in pdf_base64:
                        pdf_base64 = pdf_base64.split(",", 1)[1]
                    pdf_bytes = base64.b64decode(pdf_base64)
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_bytes)
                except Exception as e:
                    print("base64 decode error:", e)

            # Priority 2: Server-side pisa rendering fallback
            if not pdf_bytes and pisa and html_content:
                try:
                    pdf_buf = io.BytesIO()
                    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buf, encoding="utf-8")
                    if not pisa_status.err:
                        pdf_bytes = pdf_buf.getvalue()
                        with open(pdf_path, "wb") as f:
                            f.write(pdf_bytes)
                except Exception as e:
                    print("pisa error:", e)

            # Send document to Telegram chat if user opened via Telegram bot
            sent_to_tg = False
            cfg = get_config()
            token = cfg.get("botToken", "")
            if pdf_bytes and token and tg_user_id.isdigit():
                try:
                    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"
                    files = {"document": (file_name, pdf_bytes, "application/pdf")}
                    data = {
                        "chat_id": tg_user_id,
                        "caption": f"📄 *Готово! Ваш PDF-разбор Instagram для @{safe_handle}*\n\nОтправлено из TargetPro AI",
                        "parse_mode": "Markdown"
                    }
                    r = requests.post(doc_url, data=data, files=files, timeout=20)
                    if r.status_code == 200 and r.json().get("ok"):
                        sent_to_tg = True
                except Exception as e:
                    print("TG sendDoc error:", e)

            resp_payload = {
                "ok": bool(pdf_bytes or sent_to_tg),
                "sentToTelegram": sent_to_tg,
                "downloadUrl": f"/pdfs/{file_name}" if (pdf_bytes and os.path.exists(pdf_path)) else "",
                "fileName": file_name
            }
            body = json.dumps(resp_payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

# ==============================================================================
# TELEGRAM BOT WORKER (BACKGROUND THREAD)
# ==============================================================================
def bot_worker_loop():
    print("TargetPro AI Telegram Bot Worker thread started...")
    offset = 0
    last_menu_url = ""

    while True:
        try:
            cfg = get_config()
            msgs = read_json(MESSAGES_PATH)
            token = cfg.get("botToken", "").strip()

            if not token:
                time.sleep(3)
                continue

            app_url = cfg.get("publicAppUrl", "").strip()
            menu_text = msgs.get("menuButtonText", "⚡ TargetPro AI")

            if app_url and app_url != last_menu_url and app_url.startswith("https://"):
                res = tg_api_call(token, "setChatMenuButton", {
                    "menu_button": {
                        "type": "web_app",
                        "text": menu_text,
                        "web_app": {"url": app_url}
                    }
                })
                if res.get("ok"):
                    last_menu_url = app_url
                    print(f"Updated Telegram Menu Button to: {app_url}")

            upd_res = tg_api_call(token, f"getUpdates?offset={offset}&timeout=15")
            if not upd_res.get("ok"):
                time.sleep(2)
                continue

            for upd in upd_res.get("result", []):
                offset = upd["update_id"] + 1
                chat_id = None
                user_id = None
                first_name = msgs.get("defaultName", "Гость")
                username = ""
                text_in = ""
                is_callback = False
                callback_id = None

                if "message" in upd:
                    msg = upd["message"]
                    if msg.get("chat", {}).get("type") != "private":
                        continue
                    chat_id = msg["chat"]["id"]
                    user = msg.get("from", {})
                    user_id = user.get("id")
                    first_name = user.get("first_name", first_name)
                    username = user.get("username", "")
                    text_in = msg.get("text", "")
                elif "callback_query" in upd:
                    cq = upd["callback_query"]
                    is_callback = True
                    callback_id = cq["id"]
                    chat_id = cq.get("message", {}).get("chat", {}).get("id")
                    user = cq.get("from", {})
                    user_id = user.get("id")
                    first_name = user.get("first_name", first_name)
                    username = user.get("username", "")

                if not chat_id:
                    continue

                log_lead(f"BOT_USER: {first_name} (user:{username} id:{user_id}) | Msg: {text_in}")

                chan = cfg.get("channelUsername", "@TargetPro_ai")
                chan_url = cfg.get("channelUrl", "https://t.me/TargetPro_ai")
                insta_user = cfg.get("instagramUsername", "@imamaliev.ads")
                insta_url = cfg.get("instagramUrl", "https://instagram.com/imamaliev.ads")

                is_member = False
                check_res = tg_api_call(token, f"getChatMember?chat_id={urllib.parse.quote(chan)}&user_id={user_id}")
                if check_res.get("ok"):
                    status = check_res.get("result", {}).get("status", "")
                    if status in ["creator", "administrator", "member", "restricted"]:
                        is_member = True

                if is_member:
                    if is_callback:
                        tg_api_call(token, "answerCallbackQuery", {
                            "callback_query_id": callback_id,
                            "text": msgs.get("toastConfirmed", "Доступ открыт!"),
                            "show_alert": False
                        })

                    msg_template = msgs.get("unlockedText", "Добро пожаловать в TargetPro AI!")
                    msg_text = msg_template.replace("{name}", first_name).replace("{url}", app_url)

                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": msgs.get("btnOpenApp", "⚡ Открыть TargetPro AI"), "web_app": {"url": app_url}}],
                            [{"text": msgs.get("btnOpenBrowser", "🌐 Открыть в браузере"), "url": app_url}],
                            [{"text": msgs.get("btnOpenChannel", "📢 Наш канал"), "url": chan_url}],
                            [{"text": msgs.get("btnOpenInsta", "📸 Наш Instagram"), "url": insta_url}],
                            [{"text": msgs.get("btnContactOwner", "💬 Связаться с автором"), "url": "https://t.me/johaxzx"}]
                        ]
                    }
                else:
                    if is_callback:
                        tg_api_call(token, "answerCallbackQuery", {
                            "callback_query_id": callback_id,
                            "text": msgs.get("alertNotSubbed", "Вы ещё не подписались на канал!"),
                            "show_alert": True
                        })
                        continue

                    msg_template = msgs.get("lockedText", "Для доступа подпишитесь на канал:")
                    msg_text = msg_template.replace("{name}", first_name)

                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": msgs.get("btnSubscribeTg", "1. Подписаться на Telegram"), "url": chan_url}],
                            [{"text": msgs.get("btnSubscribeInsta", "2. Подписаться на Instagram"), "url": insta_url}],
                            [{"text": msgs.get("btnVerify", "3. Я подписался — Проверить"), "callback_data": "check_sub"}]
                        ]
                    }

                tg_api_call(token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": msg_text,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup
                })
        except Exception as e:
            time.sleep(3)

def main():
    t = threading.Thread(target=bot_worker_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", PORT), TargetProHandler)
    print(f"TargetPro AI Server & Telegram Bot Worker running on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
