from pathlib import Path
import re


def test_historical_business_qa_route_redirects_without_adding_backend_chat_endpoint() -> None:
    api_text = Path("api/app.py").read_text(encoding="utf-8")
    route_paths = re.findall(r"@app\.(?:get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", api_text)

    forbidden = [path for path in route_paths if "chat" in path.lower() or "business-qa" in path.lower()]

    assert forbidden == []
    route_text = Path("frontend/app/workspaces/[workspaceId]/business-qa/page.tsx").read_text(encoding="utf-8")
    assert 'redirect(`/workspaces/${workspaceId}/analysis`)' in route_text
    assert not Path("frontend/components/BusinessQAPreview.tsx").exists()
