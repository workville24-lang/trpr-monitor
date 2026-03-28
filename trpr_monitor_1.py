import json
import time
import logging
import os
import schedule
import anthropic
import httpx
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]

CHECK_INTERVAL_MINUTES = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a monitor for the Canadian TR to PR (Temporary Resident to Permanent Resident) immigration program.
Search the web for the latest status of TR to PR 2026 applications on IRCC website.

Return ONLY a valid JSON object - no markdown, no backticks, no explanation:
{
  "status": "open" or "not_open" or "unknown",
  "summary_ru": "1-2 sentence summary in Russian",
  "source": "URL or source name, or null",
  "confidence": 0-100
}

Definitions:
- open = Applications are actively being accepted RIGHT NOW on ircc.canada.ca
- not_open = Program is announced but NOT yet accepting applications
- unknown = Not enough information found
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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


def check_ircc():
    log.info("Checking TR to PR status...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    "Search for 'TR to PR 2026 Canada IRCC applications open intake' "
                    "and 'Canada temporary resident permanent resident pathway 2026'. "
                    "Are applications currently being accepted?"
                )
            }]
        )

        text = "".join(
            block.text for block in response.content
            if block.type == "text"
        )

        clean = text.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        result = json.loads(clean[start:end])
        log.info(f"Status: {result.get('status')} | Confidence: {result.get('confidence')}%")
        return result

    except Exception as e:
        log.error(f"Check error: {e}")
        return {"status": "unknown", "summary_ru": f"Error: {e}", "confidence": 0, "source": None}


alert_sent = False


def run_check():
    global alert_sent

    result = check_ircc()
    status     = result.get("status")
    confidence = result.get("confidence", 0)
    summary    = result.get("summary_ru", "-")
    now        = datetime.now().strftime("%d.%m.%Y %H:%M")

    if status == "open" and confidence >= 70:
        if not alert_sent:
            log.info("OPEN! Sending alert...")
            send_telegram(
                f"TR TO PR - ZAYAVKI OTKRYTY!\n\n"
                f"{summary}\n\n"
                f"Podavayte nemedlenno:\n"
                f"https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/tr-pr-pathway.html\n\n"
                f"Time: {now}"
            )
            alert_sent = True
        else:
            log.info("Alert already sent.")
    else:
        if status != "open":
            alert_sent = False
        log.info(f"Check done: {status} ({confidence}%) - not open yet")


def main():
    log.info("=" * 50)
    log.info("TR to PR Monitor started")
    log.info(f"Interval: every {CHECK_INTERVAL_MINUTES} minutes")
    log.info("=" * 50)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    send_telegram(
        f"TR to PR Monitor started\n"
        f"Will check IRCC every {CHECK_INTERVAL_MINUTES} minutes.\n"
        f"Will alert when applications open!\n"
        f"Start: {now}"
    )

    run_check()

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_check)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
