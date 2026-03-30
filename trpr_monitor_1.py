import time
import logging
import os
import httpx
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["8633052932:AAHduQEu8c2c_RduDBqODxmnvyRR521yLgI"]
TELEGRAM_CHAT_ID   = os.environ["1142832493"]

CHECK_INTERVAL_SECONDS = 300  # каждые 5 минут

URLS_TO_MONITOR = [
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/tr-pr-pathway.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/news.html",
]

KEYWORDS_OPEN = [
    "apply now",
    "applications are open",
    "intake is open",
    "submit your application",
    "start your application",
    "application portal",
    "now accepting",
    "open for applications",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    try:
        r = httpx.post(url, json=payload, timeout=10)
        r.raise_for_status()
        log.info("Telegram: message sent OK")
        return True
    except Exception as e:
        log.error(f"Telegram error: {e}")
        return False


def check_page(url):
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        content = r.text.lower()
        for keyword in KEYWORDS_OPEN:
            if keyword.lower() in content:
                return True, keyword
        return False, None
    except Exception as e:
        log.error(f"Error fetching {url}: {e}")
        return False, None


alert_sent = False


def run_check():
    global alert_sent
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    log.info(f"Checking IRCC pages... {now}")

    for url in URLS_TO_MONITOR:
        found, keyword = check_page(url)
        if found:
            if not alert_sent:
                log.info(f"OPEN! Found keyword: '{keyword}' on {url}")
                send_telegram(
                    f"TR TO PR - ZAYAVKI OTKRYTY!\n\n"
                    f"Naydeno: '{keyword}'\n\n"
                    f"Podavayte nemedlenno:\n"
                    f"{url}\n\n"
                    f"Time: {now}"
                )
                alert_sent = True
            return

    if not alert_sent:
        log.info("Not open yet - no keywords found")


def main():
    log.info("=" * 50)
    log.info("TR to PR Monitor started (no API - free!)")
    log.info(f"Checking every {CHECK_INTERVAL_SECONDS // 60} minutes")
    log.info("=" * 50)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    send_telegram(
        f"TR to PR Monitor started!\n"
        f"Checking IRCC directly every {CHECK_INTERVAL_SECONDS // 60} minutes.\n"
        f"No API costs - completely free!\n"
        f"Start: {now}"
    )

    while True:
        run_check()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
