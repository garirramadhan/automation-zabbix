import asyncio
from playwright.async_api import async_playwright
import time
import requests
from datetime import datetime
import os
import winsound
import ctypes
import wave
import struct
import math
import io
import re

# ==========================================
# IMPOR MODUL OCR & KONFIGURASI TESSERACT
# ==========================================
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ==========================================
# 1. KONFIGURASI URL & TOKEN (TELEGRAM & WHATSAPP)
# ==========================================
ZABBIX_LOGIN_URL = "https://zbx-fwa.ije-weave.com/zabbix/"
GRAPH_URL = "https://zbx-fwa.ije-weave.com/zabbix/zabbix.php?action=charts.view&filter_hostids%5B0%5D=10803&filter_show=1&filter_set=1&from=now-1h&to=now"
HOST_DASHBOARD_URL = "https://zbx-fwa.ije-weave.com/zabbix/zabbix.php?action=host.dashboard.view&hostid=10803"

ZABBIX_USER = "noc"
ZABBIX_PASS = "asdqwe12345"

TELEGRAM_TOKEN = "8727755067:AAGoj_xcj4TD1zR9bZQvQt5msdSc1tLBg7w"
CHAT_ID = "-5466031318"

# KONFIGURASI WHATSAPP TARGET (Lokal Node.js)
WHATSAPP_TARGET = "120363428673062777@g.us"

LAST_UPDATE_ID = 0

if not os.path.exists("screenshot"):
    os.makedirs("screenshot")

# ==========================================
# 2. GENERATOR SUARA NADA MURNI SEAMLESS (.WAV)
# ==========================================
def create_tone_file():
    filename = "crit_tone.wav"
    if not os.path.exists(filename):
        sample_rate = 11025
        frequency = 4000  
        duration = 0.2    
        num_frames = int(sample_rate * duration)
        
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(1) 
            wav_file.setsampwidth(2) 
            wav_file.setframerate(sample_rate)
            for i in range(num_frames):
                value = int(32767 * 0.7 * math.sin(2 * math.pi * frequency * i / sample_rate))
                wav_file.writeframes(struct.pack('<h', value))
    return filename

TONE_FILE = create_tone_file()

# ==========================================
# 3. FUNGSI PENGIRIMAN PESAN & MEDIA
# ==========================================
def send_photo_telegram(image_path, caption_pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    clean_caption = caption_pesan.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
    try:
        with open(image_path, "rb") as foto:
            payload = {"chat_id": CHAT_ID, "caption": clean_caption}
            files = {"photo": foto}
            response = requests.post(url, data=payload, files=files, timeout=20)
            if response.status_code == 200:
                print(f"✅ Foto Telegram ({image_path.split('/')[-1]}) berhasil dikirim!")
            else:
                print(f"⚠️ Gagal kirim foto Telegram. Alasan: {response.text}")
    except Exception as e:
        print("❌ Error koneksi pengiriman foto Telegram:", e)

def send_message_telegram(teks_pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": teks_pesan, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Gagal kirim pesan Telegram. Alasan: {response.text}")
    except Exception as e:
        print("❌ Error koneksi pesan Telegram:", e)

def kirim_whatsapp(pesan_teks):
    url = "http://localhost:3000/send"
    payload = {
        "target": WHATSAPP_TARGET,
        "message": pesan_teks,
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Notifikasi WhatsApp berhasil dikirim (Lokal Node.js)!")
        else:
            print("⚠️ Gagal kirim WhatsApp:", response.text)
    except Exception as e:
        print("❌ Error koneksi ke WA Local Bridge:", e)

def kirim_foto_whatsapp(image_path, caption_pesan):
    url = "http://localhost:3000/send"
    clean_caption = caption_pesan.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    payload = {
        "target": WHATSAPP_TARGET,
        "message": clean_caption,
        "imagePath": image_path
    }
    try:
        response = requests.post(url, json=payload, timeout=25)
        if response.status_code == 200:
            print("✅ Foto screenshot WhatsApp berhasil dikirim")
        else:
            print("⚠️ Gagal kirim foto WhatsApp:", response.text)
    except Exception as e:
        print("❌ Error koneksi kirim foto WA Local Bridge:", e)

# ==========================================
# 4. FUNGSI ALARM LAPTOP & AUDIO 
# ==========================================
def bunyikan_alarm_laptop(ada_kritis):
    try:
        if ada_kritis:
            winsound.PlaySound(TONE_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            ctypes.windll.user32.MessageBoxW(0, "ALARM KRITIS: Link Down/ICMP Ping terdeteksi di Zabbix!\n(Suara berdengung non-stop sampai Anda klik OK)", "NOC Alert - KRITIS!", 0x10)
            winsound.PlaySound(None, 0)
        else:
            for _ in range(5):
                winsound.PlaySound(TONE_FILE, winsound.SND_FILENAME)
                time.sleep(0.4) 
            ctypes.windll.user32.MessageBoxW(0, "Alarm/Masalah baru terdeteksi di Zabbix!", "NOC Alert - Warning", 0x30)
    except Exception as e:
        print("Catatan alarm audio/popup:", e)

# ==========================================
# 5. FUNGSI PENGENDALI PLAYWRIGHT, URL & OCR
# ==========================================

async def unduh_grafik_hd_dan_ocr(page, waktu_str):
    path = f"screenshot/graph_{waktu_str}.png"
    try:
        src = None
        imgs = await page.locator("img").all()
        for img in imgs:
            img_src = await img.get_attribute("src")
            if img_src and "chart2.php" in img_src:
                if img_src.startswith("/"):
                    src = ZABBIX_LOGIN_URL.split("/zabbix")[0] + img_src
                elif img_src.startswith("chart2.php"):
                    src = f"{ZABBIX_LOGIN_URL}/{img_src}"
                else:
                    src = img_src
                break
        
        if not src:
            print("⚠️ URL chart2.php tidak ditemukan, fallback ke screenshot halaman.")
            await page.screenshot(path=path, full_page=False)
            return path, "min = N/A | avg = N/A | max = N/A (Grafik tidak ditemukan)"

        w = 1400
        h = 800
        src2 = re.sub(r"width=\d+", f"width={w}", src)
        src2 = re.sub(r"height=\d+", f"height={h}", src2)
        src2 = re.sub(r"from=[^&]*", "from=now-1h", src2)
        src2 = re.sub(r"to=[^&]*", "to=now", src2)
        if "from=" not in src2:
            src2 += "&from=now-1h&to=now"

        resp = await page.context.request.get(src2)
        if resp.status == 200:
            img_bytes = await resp.body()
            with open(path, "wb") as f:
                f.write(img_bytes)
            print(f"✅ Berhasil mengunduh grafik HD ke: {path}")
            
            # PROSES OCR LANGSUNG TANPA PROTEKSI "NONAKTIF"
            img = Image.open(io.BytesIO(img_bytes))
            W, H = img.size
            legend = img.crop((0, int(H * 0.55), W, H))

            legend = legend.convert("L")
            legend = legend.resize((legend.width * 2, legend.height * 2))
            
            text = pytesseract.image_to_string(legend, lang="eng", config="--psm 6")
            parsed_result = parse_bits_sent_logic(text)
            
            return path, parsed_result
        else:
            print(f"⚠️ Gagal unduh HTTP {resp.status}, fallback ke screenshot.")
            await page.screenshot(path=path, full_page=False)
            return path, "min = N/A | avg = N/A | max = N/A (Gagal HTTP)"
    except Exception as e:
        print("⚠️ Error unduh_grafik_hd_dan_ocr:", e)
        await page.screenshot(path=path, full_page=True)
        return path, "min = N/A | avg = N/A | max = N/A"
    
def parse_bits_sent_logic(ocr_text):
    TARGET_LABEL = "Bits sent"
    for line in ocr_text.split("\n"):
        low = line.lower()
        if TARGET_LABEL.lower() in low and "received" not in low:
            if "no data" in low:
                return "min = 0 bps | avg = 0 bps | max = 0 bps (NO DATA)"

            tail = re.split(r"bits\s*sent", line, flags=re.IGNORECASE)[-1]

            tail_fix = re.sub(r"[\[\(][^\]\)]*[\]\)]", " ", tail)
            tail_fix = re.sub(r"\b(fava|ava|ast|min|max|avg|last)\b", " ", tail_fix, flags=re.IGNORECASE)
            tail_fix = re.sub(r"(?<![A-Za-z0-9])O(?=\s*b)", "0", tail_fix)
            tail_fix = re.sub(r"(\d)([KMGTPkmgtp])", r"\1 \2", tail_fix)
            tail_fix = re.sub(r"([KMGTPkmgtp])(b)", r"\1 \2", tail_fix)

            matches = re.findall(r"([\d]+(?:[.,]\d+)?)\s*([KMGTP]?)\s*b(?:p?s?)?\b", tail_fix, re.IGNORECASE)
            if len(matches) < 4:
                matches2 = re.findall(r"([\d]+(?:[.,]\d+)?)\s*([KMGTP]?)", tail_fix, re.IGNORECASE)
                matches2 = [(n, u) for n, u in matches2 if re.search(r"\d", n)]
                if len(matches2) >= len(matches):
                    matches = matches2

            if len(matches) >= 1:
                vals = []
                for num_str, unit in matches[:4]:
                    try:
                        num = float(num_str.replace(",", ""))
                    except:
                        continue
                    mul = {"": 1, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15}[unit.upper()]
                    vals.append(num * mul)

                if len(vals) >= 4:
                    # Menggunakan f"{nilai:.3f}".rstrip('0').rstrip('.') untuk membuang angka 0 di belakang
                    v_min_str = f"{vals[1]/1e9:.3f}".rstrip('0').rstrip('.')
                    v_avg_str = f"{vals[2]/1e9:.3f}".rstrip('0').rstrip('.')
                    v_max_str = f"{vals[3]/1e9:.3f}".rstrip('0').rstrip('.')
                    return f"min={v_min_str} Gbps | avg={v_avg_str} Gbps | max={v_max_str} Gbps"
                    
                elif len(vals) >= 1:
                    v_min = min(vals)
                    v_min_str = f"{v_min/1e9:.3f}".rstrip('0').rstrip('.')
                    v_max_str = f"{max(vals)/1e9:.3f}".rstrip('0').rstrip('.')
                    return f"min={v_min_str} Gbps | avg=N/A | max={v_max_str} Gbps"
                
    return "min = N/A | avg = N/A | max = N/A (Parsing tidak cocok)"

async def bersihkan_ui_zabbix(page):
    try:
        await page.evaluate("""() => {
            const selectorsToHide = [
                '.sidebar', 'header', '.header-title', 'footer',
                '.filter-space', '.ui-tabs-nav', '.breadcrumbs',
                '.filter-container', '.filter-btn-container',
                'form[name="zbx_filter"]', '.dashboards-header',
                'nav', '.header-right', 'div[style*="float: right"]'
            ];
            selectorsToHide.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (el) el.style.display = 'none';
                });
            });

            const style = document.createElement('style');
            style.innerHTML = `
                ::-webkit-scrollbar { display: none !important; }
                body, html { overflow: hidden !important; }
            `;
            document.head.appendChild(style);

            const wrapper = document.querySelector('.wrapper');
            if (wrapper) {
                wrapper.style.paddingLeft = '0';
                wrapper.style.marginLeft = '0';
                wrapper.style.overflow = 'hidden';
            }
            
            const article = document.querySelector('article');
            if (article) {
                article.style.padding = '0';
                article.style.margin = '0';
            }
        }""")
    except Exception:
        pass

async def paksa_realtime_dan_bersihkan_host(page):
    try:
        await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll("a")).filter(a => a.textContent.trim() === 'Last 1 hour');
            if (links.length > 0) { links[0].click(); }
        }""")
        await asyncio.sleep(1)
        await page.evaluate("""() => {
            const applies = Array.from(document.querySelectorAll("button")).filter(b => b.textContent.trim() === 'Apply');
            for (let btn of applies) {
                if (btn.offsetWidth > 0 || btn.offsetHeight > 0) {
                    btn.click();
                    const panel = btn.closest('div.ui-tabs-panel') || btn.closest('div.filter-space') || btn.closest('table');
                    if (panel) { panel.style.display = 'none'; }
                    break;
                }
            }
        }""")
    except Exception:
        pass

async def ss_tab_dash(page, waktu_str):
    await page.bring_to_front()
    try:
        await page.wait_for_selector('table.list-table', timeout=5000)
    except Exception:
        pass
        
    await asyncio.sleep(0.8) 
    await bersihkan_ui_zabbix(page) 
    await asyncio.sleep(0.2) 
    
    path = f"screenshot/dash_{waktu_str}.png"
    try:
        await page.screenshot(path=path, full_page=False)
    except Exception as e:
        print("Keterangan error screenshot dashboard:", e)
        await page.screenshot(path=path)
    return path

async def ss_tab_host(page, waktu_str):
    await page.bring_to_front()
    await page.set_viewport_size({"width": 1400, "height": 900})
    await page.reload(wait_until="domcontentloaded")
    
    try:
        await page.wait_for_selector('.dashboard-grid-widget, .flickerfree-container', timeout=10000)
    except Exception:
        pass
        
    await asyncio.sleep(3.5)
    await paksa_realtime_dan_bersihkan_host(page)
    await bersihkan_ui_zabbix(page)
    await asyncio.sleep(0.5)
    
    path = f"screenshot/host_{waktu_str}.png"
    try:
        element = page.locator('.dashboard-grid-widget, .flickerfree-container').first
        box = await element.bounding_box()
        
        if box:
            await page.screenshot(path=path, clip={
                'x': box['x'],
                'y': box['y'],
                'width': box['width'],
                'height': box['height']
            })
        else:
            await page.screenshot(path=path, full_page=False)
    except Exception as e:
        print("Keterangan error screenshot host:", e)
        await page.screenshot(path=path, full_page=True)
        
    return path

# ==========================================
# 6. PENGECEK PERINTAH TELEGRAM
# ==========================================
async def cek_perintah_telegram(tab_dashboard, tab_graph, tab_host):
    global LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=1"
    try:
        res = requests.get(url, timeout=3).json()
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                LAST_UPDATE_ID = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"].strip().lower()
                    chat_id_from = str(update["message"]["chat"]["id"])
                    
                    if chat_id_from == CHAT_ID:
                        waktu_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        if "/cekstatus" in text:
                            print("[PERINTAH] /cekstatus diterima, mengambil screenshot...")
                            f_host = await ss_tab_host(tab_host, waktu_str)
                            f_dash = await ss_tab_dash(tab_dashboard, waktu_str)
                            f_graph, _ = await unduh_grafik_hd_dan_ocr(tab_graph, waktu_str)
                            
                            send_photo_telegram(f_dash, "Current Dashboards Zabbix")
                            send_photo_telegram(f_graph, "Traffic Graphs View")
                            send_photo_telegram(f_host, "Host Dashboards")
                            
                            kirim_foto_whatsapp(f_dash, "Current Dashboards Zabbix")
                            kirim_foto_whatsapp(f_graph, "Traffic Graphs View")
                            kirim_foto_whatsapp(f_host, "Host Dashboards")
                            
                            await tab_dashboard.bring_to_front()
                            print("[PERINTAH] /cekstatus selesai dieksekusi.")
                            
                        elif "/cekdashboards" in text or "/cekdashboard" in text:
                            print("[PERINTAH] /cekdashboards received, taking a screenshot...")
                            f_dash = await ss_tab_dash(tab_dashboard, waktu_str)
                            
                            send_photo_telegram(f_dash, "Current Dashboards Zabbix")
                            kirim_foto_whatsapp(f_dash, "Current Dashboards Zabbix")
                            
                            await tab_dashboard.bring_to_front()
                            print("[PERINTAH] /cekdashboards has been executed.")
                            
    except Exception as e:
        print("❌ Error pada cek_perintah_telegram:", e)

# ==========================================
# 7. PROSES UTAMA ROBOT (ASYNC PLAYWRIGHT)
# ==========================================
async def main():
    print("Memanaskan mesin Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        
        print("Tab 1: Membuka halaman login Zabbix...")
        tab_dashboard = await context.new_page()
        await tab_dashboard.goto(ZABBIX_LOGIN_URL)
        await tab_dashboard.fill('input[name="name"]', ZABBIX_USER)
        await tab_dashboard.fill('input[name="password"]', ZABBIX_PASS)
        await tab_dashboard.click('#enter')

        print("Tab 2: Membuka tab untuk Graphs View...")
        tab_graph = await context.new_page()
        await tab_graph.goto(GRAPH_URL)
        await asyncio.sleep(3)
        await bersihkan_ui_zabbix(tab_graph)

        print("Tab 3: Membuka tab untuk Host Dashboards...")
        tab_host = await context.new_page()
        await tab_host.goto(HOST_DASHBOARD_URL)
        await asyncio.sleep(3)
        await bersihkan_ui_zabbix(tab_host)
        print("-> BOT PLAYWRIGHT ZABBIX SIAP BERJALAN SENDIRI!\n")
        print("-" * 50)
        
        await tab_dashboard.bring_to_front()

        first_run = True   
        alarm_lama = set()
        
        now = datetime.now()
        seconds_to_next_hour = ((59 - now.minute) * 60) + (60 - now.second)
        next_hourly_report = time.time() + seconds_to_next_hour

        while True:
            try:
                # ==========================================
                # BLOK LAPORAN HOURLY 
                # ==========================================
                if time.time() >= next_hourly_report:
                    print("[HOURLY REPORT] Waktu jam bulat tercapai, mengekstrak statistik & grafik Traffic...")
                    waktu_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    time_report = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    
                    f_graph, info_traffic = await unduh_grafik_hd_dan_ocr(tab_graph, waktu_str)
                    
                    pesan_wa = (
                        f"📊 *TRAFFIC REPORT ZABBIX* 📊\n"
                        f"📅 time: {time_report}\n\n"
                        f"{info_traffic}"
                    )
                    
                    pesan_tg = (
                        f"📊 <b>TRAFFIC REPORT ZABBIX</b>\n"
                        f"📅 {time_report}\n\n"
                        f"<code>{info_traffic}</code>"
                    )
                    
                    send_photo_telegram(f_graph, pesan_tg)
                    kirim_foto_whatsapp(f_graph, pesan_wa)
                    
                    await tab_dashboard.bring_to_front()
                    next_hourly_report += 3600

               # ==========================================
                # BLOK PEMERIKSAAN ALARM & STATUS KESEHATAN
                # ==========================================
                print("[Tab 1 - Dashboard] Memeriksa alarm...")
                await tab_dashboard.bring_to_front()
                await asyncio.sleep(2)
                
                try:
                    tabel_masalah = tab_dashboard.locator('.list-table').first
                    rows = await tabel_masalah.locator('tr:visible').all()
                except Exception:
                    rows = []
                    
                alarm_baru_terdeteksi = []
                total_critical = 0
                total_warning = 0

                for row in rows:
                    try:
                        text = await row.inner_text()
                        text_clean = text.strip()
                        text_lower = text_clean.lower()
                        
                        if not text_clean or "severity" in text_lower or "status" in text_lower or "host" in text_lower or "time" in text_lower or "no data found" in text_lower or "today" in text_lower or "problems are shown" in text_lower or "resolved" in text_lower or "ok" in text_lower:
                            continue
                            
                        cols_text = await row.locator('td').all_inner_texts()
                        
                        if len(cols_text) >= 4:
                            host_name = cols_text[2].strip()
                            problem_desc = cols_text[3].strip()
                            
                            if host_name and problem_desc:
                                problem_clean = problem_desc.replace('\n', ' - ')
                                identitas_unik = f"{host_name}_{problem_clean}"
                                pesan_rapi = f"[{host_name}] {problem_clean}"
                                
                                # Deteksi tingkat keparahan (Severity) berdasarkan teks atau baris
                                row_html = await row.inner_html()
                                if "severity-bg-6" in row_html or "disaster" in row_html or "high" in row_html or "link down" in text_lower or "icmp ping" in text_lower:
                                    total_critical += 1
                                else:
                                    total_warning += 1

                                if first_run:
                                    alarm_lama.add(identitas_unik)
                                else:
                                    if identitas_unik not in alarm_lama:
                                        alarm_baru_terdeteksi.append(pesan_rapi)
                                        alarm_lama.add(identitas_unik)
                    except Exception:
                        continue

                if first_run:
                    print(f"[INISIALISASI] Berhasil menghafal {len(alarm_lama)} alarm lama. Robot Playwright siaga penuh.")
                    first_run = False
                    continue
                            
                if alarm_baru_terdeteksi:
                    waktu_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    waktu_laporan = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    
                    ada_kritis = total_critical > 0
                    bunyikan_alarm_laptop(ada_kritis)
                    
                    f_host = await ss_tab_host(tab_host, waktu_str)
                    f_dash = await ss_tab_dash(tab_dashboard, waktu_str)
                    f_graph, info_traffic = await unduh_grafik_hd_dan_ocr(tab_graph, waktu_str)
                    
                    # Menentukan Status Sistem Berdasarkan Jumlah Alarm
                    if total_critical > 0:
                        status_sistem = "🔴 *CRITICAL / GANGGUAN BERAT*"
                    elif total_warning > 0:
                        status_sistem = "🟡 *WARNING / PERHATIAN*"
                    else:
                        status_sistem = "🟢 *NORMAL / STABIL*"

                    header_laporan = (
                        f"*ZABBIX STATUS REPORT*\n"
                        f"Time: {time_report}\n\n"
                        f"Status Sistem: {status_sistem}\n"
                        f"Traffic Interface: {info_traffic}\n"
                        f"Active Problems: {total_critical} Critical, {total_warning} Warning\n\n"
                    )
                        
                    daftar_alarm = ""
                    for alarm in alarm_baru_terdeteksi:
                        daftar_alarm += f"🔻 {alarm}\n\n"
                    
                    caption_tg = header_laporan + daftar_alarm + "🛠️ Bukti visual terlampir di bawah.\n\n[1/3] Current Problems"
                    send_photo_telegram(f_dash, caption_tg)
                    send_photo_telegram(f_graph, "[2/3] Traffic Graphs View")
                    send_photo_telegram(f_host, "[3/3] Host Dashboards")
                    
                    caption_gabungan = header_laporan + daftar_alarm + "*Dashboard Zabbix*"
                    kirim_foto_whatsapp(f_dash, caption_gabungan)
                    
                    await tab_dashboard.bring_to_front()
                else:
                    print("[Tab 1 - Dashboard] Aman, tidak ada alarm baru.")

            except Exception as loop_err:
                print(f"⚠️ [WARNING KONEKSI/BROWSER] Terdeteksi gangguan jaringan: {loop_err}")
                print("🔄 Melanjutkan pemantauan, mencoba menyambungkan ulang...")

            for _ in range(150):
                await cek_perintah_telegram(tab_dashboard, tab_graph, tab_host)
                await asyncio.sleep(2)

if __name__ == "__main__":
    while True:
        try:
            print("\n[SYSTEM] Memulai sistem pemantauan NOC Zabbix...")
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n[SYSTEM] Robot Playwright dihentikan secara manual oleh Anda.")
            break 
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Bot mengalami gangguan/crash! Penyebab: {e}")
            print("[SYSTEM] Menunggu 10 detik sebelum Auto-Restart...\n")
            time.sleep(10)