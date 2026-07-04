from pathlib import Path
import re


def test_p14_business_qa_preview_does_not_add_backend_chat_endpoint() -> None:
    api_text = Path("api/app.py").read_text(encoding="utf-8")
    route_paths = re.findall(r"@app\.(?:get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", api_text)

    forbidden = [path for path in route_paths if "chat" in path.lower() or "business-qa" in path.lower()]

    assert forbidden == []
