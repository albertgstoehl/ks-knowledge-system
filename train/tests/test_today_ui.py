import pytest


@pytest.mark.asyncio
async def test_today_page_has_marathon_card(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "MARATHON" in html
    assert "weeks to race" in html
