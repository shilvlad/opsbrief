"""Отправка только отдельно подготовленной обезличенной голосовой сводки."""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description="Передать согласованную голосовую сводку на VPS")
    parser.add_argument("--file", type=Path, required=True,
                        help="JSON только с разрешёнными к отправке сведениями")
    parser.add_argument("--url", default=os.getenv("OPSBRIEF_API_URL", ""))
    args = parser.parse_args()
    token = os.getenv("OPSBRIEF_UPLOAD_TOKEN", "")
    if not args.url.startswith("https://") or not token:
        parser.error("Нужны HTTPS OPSBRIEF_API_URL и OPSBRIEF_UPLOAD_TOKEN")
    content = json.loads(args.file.read_text(encoding="utf-8"))
    if set(content) != {"date", "timezone", "meetings", "recommendations"}:
        parser.error("Разрешены только date, timezone, meetings, recommendations")
    if not isinstance(content["meetings"], list) or not isinstance(content["recommendations"], list):
        parser.error("meetings и recommendations должны быть массивами")
    request = Request(
        args.url.rstrip("/") + "/api/v1/brief",
        data=json.dumps(content, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        print(response.read().decode())


if __name__ == "__main__":
    main()
