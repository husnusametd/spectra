"""SMTP ile HTML e-posta gönderen modül."""
from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

import aiosmtplib
from jinja2 import Template

from spectra.utils import load_config

CFG = load_config()
SMTP_CFG = CFG["smtp"]

TABLE_TMPL = Template(
    """
    <table border="1" cellpadding="4" cellspacing="0">
      <tr>
        <th>Rank</th><th>Ticker</th><th>Signal</th><th>Conviction</th>
        <th>Entry</th><th>SL</th><th>TP1</th><th>TP2</th><th>TS</th>
      </tr>
      {% for r in rows %}
      <tr>
        <td>{{r.rank}}</td><td>{{r.ticker}}</td><td>{{r.signal}}</td>
        <td>{{r.conviction}}</td><td>{{r.entry}}</td><td>{{r.sl}}</td>
        <td>{{r.tp1}}</td><td>{{r.tp2}}</td><td>{{r.ts}}</td>
      </tr>
      {% endfor %}
    </table>
    """
)


async def send_email(rows: List[Dict]):
    """HTML tabloyu veya tek satır mesajı e-posta olarak yollar."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[Spectra] Kripto Sinyal Raporu"
    msg["From"] = SMTP_CFG["from_addr"]
    msg["To"] = SMTP_CFG["to_addr"]

    if rows:
        body_html = TABLE_TMPL.render(rows=rows)
    else:
        body_html = "No qualifying signals this run."

    msg.attach(MIMEText(body_html, "html"))

    # Eğer SMTP kimlik bilgileri tanımlı değilse, mail göndermek yerine konsola yaz.
    if not SMTP_CFG.get("user") or SMTP_CFG.get("user") == "${SMTP_USER}":
        logging.info("SMTP creds boş, e-posta yerine HTML çıktısı loglanıyor (rows=%s)", len(rows))
        print("\n==== HTML EMAIL PREVIEW ====")
        print(body_html)
        print("==== END PREVIEW ===\n")
        return

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_CFG["host"],
            port=int(SMTP_CFG["port"]),
            username=SMTP_CFG["user"],
            password=SMTP_CFG["password"],
            start_tls=True,
        )
        logging.info("E-mail sent – %s rows", len(rows))
    except Exception as exc:
        logging.exception("E-mail failed: %s", exc)

