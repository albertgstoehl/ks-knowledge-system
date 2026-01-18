import os
import tempfile
from fastapi.testclient import TestClient
from src.main import app
from src.routers.plans import parse_frontmatter


def test_parse_frontmatter_with_templates():
    content = """---
templates:
  Push:
    - Bench
    - Press
---
# Title
Body"""
    frontmatter, markdown = parse_frontmatter(content)
    assert frontmatter == {"templates": {"Push": ["Bench", "Press"]}}
    assert markdown.strip().startswith("# Title")


def test_parse_frontmatter_no_frontmatter():
    content = "# Just Markdown\nNo frontmatter here."
    frontmatter, markdown = parse_frontmatter(content)
    assert frontmatter == {}
    assert markdown == content


def test_parse_frontmatter_invalid_yaml():
    content = """---
invalid: [unclosed
---
# Title"""
    frontmatter, markdown = parse_frontmatter(content)
    assert frontmatter == {}
    assert markdown == content


def test_plan_register_and_fetch_current():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["PLAN_DIR"] = tmp_dir
        with TestClient(app) as client:
            payload = {"title": "Plan A", "markdown": "# A", "carry_over_notes": ""}
            response = client.post("/api/plan/register", json=payload)
            assert response.status_code == 200

            current = client.get("/api/plan/current")
            assert current.status_code == 200
            assert current.json()["title"] == "Plan A"
            assert current.json()["templates"] == {}


def test_plan_with_frontmatter_templates():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["PLAN_DIR"] = tmp_dir
        with TestClient(app) as client:
            # Old format (string list) - should be normalized to objects
            markdown_with_frontmatter = """---
templates:
  Push:
    - Bench Press
    - Shoulder Press
  Pull:
    - Rows
    - Pulldowns
---
# My Training Plan

Some content here.
"""
            payload = {
                "title": "Plan With Templates",
                "markdown": markdown_with_frontmatter,
                "carry_over_notes": "",
            }
            response = client.post("/api/plan/register", json=payload)
            assert response.status_code == 200
            
            # Verify register response includes parsed templates
            data = response.json()
            
            # Templates should be normalized to objects with name and muscles
            assert data["templates"] == {
                "Push": [
                    {"name": "Bench Press", "muscles": []},
                    {"name": "Shoulder Press", "muscles": []},
                ],
                "Pull": [
                    {"name": "Rows", "muscles": []},
                    {"name": "Pulldowns", "muscles": []},
                ],
            }
            
            # Markdown should have frontmatter stripped
            assert data["markdown"].startswith("# My Training Plan")
            assert "---" not in data["markdown"]


def test_plan_with_muscle_groups():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["PLAN_DIR"] = tmp_dir
        with TestClient(app) as client:
            # New format with muscle groups
            markdown_with_muscles = """---
templates:
  Push:
    - name: Bench Press
      muscles: [chest, triceps]
    - name: Shoulder Press
      muscles: [shoulders]
---
# My Training Plan
"""
            payload = {
                "title": "Plan With Muscles",
                "markdown": markdown_with_muscles,
                "carry_over_notes": "",
            }
            response = client.post("/api/plan/register", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            
            # Templates should include muscle groups
            assert data["templates"] == {
                "Push": [
                    {"name": "Bench Press", "muscles": ["chest", "triceps"]},
                    {"name": "Shoulder Press", "muscles": ["shoulders"]},
                ],
            }
