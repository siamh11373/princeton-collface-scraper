from datetime import UTC, datetime, timedelta

from collface_scraper.fetch import Pacer, retry_after


def test_pacer_spaces_request_starts():
    now = [10.0]
    sleeps = []

    def sleep(value):
        sleeps.append(value)
        now[0] += value

    pacer = Pacer(2, clock=lambda: now[0], sleep=sleep)
    pacer.wait()
    pacer.wait()
    pacer.wait()
    assert sleeps == [0.5, 0.5]


def test_retry_after_supports_seconds_and_http_dates():
    now = datetime(2026, 9, 14, tzinfo=UTC)
    assert retry_after("12", now=now) == 12
    assert retry_after("invalid", now=now) is None
    future = now + timedelta(seconds=30)
    assert retry_after(future.strftime("%a, %d %b %Y %H:%M:%S GMT"), now=now) == 30
