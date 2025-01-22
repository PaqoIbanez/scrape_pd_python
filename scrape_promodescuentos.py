import re
import time
import random
import os
import requests  # para enviar mensaje a Telegram

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ==== CONFIGURACIONES TELEGRAM ====
TELEGRAM_BOT_TOKEN = "7374238596:AAFYpFCAxUWHmGmGFVhJBhseC3ByEyYIX2A"   # <--- pon el token real
TELEGRAM_CHAT_ID = "1012523562"      # <--- pon el chat_id real

# Archivo donde se guarda la lista de ofertas ya notificadas
SEEN_FILE = "seen_hot_deals.txt"

# ---- Funciones utilitarias para "ya vistas" ----
def load_seen_deals(filepath):
    if not os.path.isfile(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_seen_deals(filepath, seen_deals):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in seen_deals:
            f.write(item + "\n")

# ---- Función para enviar mensaje por Telegram ----
def send_telegram_message(message):
    """
    Envía 'message' al chat TELEGRAM_CHAT_ID usando TELEGRAM_BOT_TOKEN.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(">>> [WARN] Falta configurar TOKEN o CHAT_ID de Telegram.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(">>> Mensaje Telegram enviado OK")
        else:
            print(f">>> [ERROR] Telegram resp: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f">>> [ERROR] Excepción enviando Telegram: {e}")

# ---- SCRAPING PRINCIPAL ----
def scrape_promodescuentos_hot():
    url = "https://www.promodescuentos.com/hot"

    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)

        html = driver.page_source
        
        with open("debug_degrees.html", "w", encoding="utf-8") as f:
            f.write(html)
            print("Archivo debug_degrees.html guardado para inspección manual.")
            
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.thread")

    deals_data = []
    for art in articles:
        # Temperatura
        temp_element = art.select_one(".cept-vote-temp")
        if not temp_element:
            continue
        temp_text = temp_element.get_text(strip=True)
        m_temp = re.search(r"(\d+(\.\d+)?)", temp_text)
        if not m_temp:
            continue
        temperature = float(m_temp.group(1))

        # Antigüedad (horas)
        time_ribbon = art.select_one(".metaRibbon span")
        if not time_ribbon:
            continue
        posted_text = time_ribbon.get_text(strip=True)

        # Parseamos "(\d+) h" y "(\d+) m"
        hours = 0
        minutes = 0
        m_hrs = re.search(r"(\d+)\s*h", posted_text)
        if m_hrs:
            hours = int(m_hrs.group(1))
        m_min = re.search(r"(\d+)\s*m", posted_text)
        if m_min:
            minutes = int(m_min.group(1))
        total_hours = hours + (minutes / 60.0)

        # Título y link
        title_element = art.select_one(".cept-tt")
        if not title_element:
            continue
        title = title_element.get_text(strip=True)
        link = title_element["href"] if title_element.has_attr("href") else ""
        if link.startswith("/"):
            link = "https://www.promodescuentos.com" + link

        deals_data.append({
            "title": title,
            "url": link,
            "temperature": temperature,
            "hours_since_posted": total_hours
        })

    return deals_data

def filter_new_hot_deals(deals, threshold_temp=100, max_hours=8):
    filtered = []
    for d in deals:
        if d["temperature"] > threshold_temp and d["hours_since_posted"] < max_hours:
            filtered.append(d)
    return filtered


def main():
    seen_deals = load_seen_deals(SEEN_FILE)

    while True:
        print("== Revisando 'Hot' Promodescuentos... ==")
        deals = scrape_promodescuentos_hot()
        hot_deals_4h_200 = filter_new_hot_deals(deals, threshold_temp=100, max_hours=8)

        # Comparar con 'seen_deals'
        new_deals = []
        for deal in hot_deals_4h_200:
            if deal["url"] not in seen_deals:
                new_deals.append(deal)

        if new_deals:
            print(f"== Se encontraron {len(new_deals)} ofertas NUEVAS con >200°, <4h ==")
            for d in new_deals:
                info = (f"- {d['temperature']:.0f}° | {d['hours_since_posted']:.1f}h | "
                        f"{d['title']} \n{d['url']}")
                print(info)

                # Notificar por Telegram
                send_telegram_message(f"Nueva oferta HOT:\n{info}")

                # Añadir a seen_deals
                seen_deals.add(d["url"])
        else:
            print("No hay ofertas nuevas con >200° y <4h.")

        save_seen_deals(SEEN_FILE, seen_deals)

        # Esperar aleatoriamente 2..20 min
        wait_seconds = random.randint(2 * 60, 20 * 60)
        print(f"Esperando {wait_seconds//60} min {wait_seconds%60} seg...\n")
        time.sleep(wait_seconds)

if __name__ == "__main__":
    main()
