from src import scheduler


def test_scheduler_exports_ensure_youtube_blocked():
    assert hasattr(scheduler, "ensure_youtube_blocked")
    assert callable(scheduler.ensure_youtube_blocked)
