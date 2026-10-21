"""Загрузка полного списка событий и рекомендаций в OpsBrief API."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def send_payload(content, url, token):
    parts = urlsplit(url)
    local = parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}
    if not (parts.scheme == "https" or local) or not parts.netloc or not token:
        raise ValueError("Нужны OPSBRIEF_API_URL (HTTPS или localhost HTTP) и OPSBRIEF_UPLOAD_TOKEN")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("OPSBRIEF_API_URL должен содержать только базовый адрес")
    if set(content) != {"date", "timezone", "meetings", "recommendations"}:
        raise ValueError("Нужны date, timezone, meetings, recommendations")
    if any(not isinstance(content[k], list) or any(not isinstance(s, str) for s in content[k])
           for k in ("meetings", "recommendations")):
        raise ValueError("meetings и recommendations должны быть массивами строк")
    request = Request(
        url.rstrip("/") + "/api/v1/brief",
        data=json.dumps(content, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description="Отправить полную сводку на OpsBrief API")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--url", default=os.getenv("OPSBRIEF_API_URL", ""))
    args = parser.parse_args()
    payload = json.loads(args.file.read_text(encoding="utf-8"))
    print(json.dumps(send_payload(payload, args.url, os.getenv("OPSBRIEF_UPLOAD_TOKEN", "")), ensure_ascii=False))


if __name__ == "__main__":
    main()
