import pytest

from app.services import scheduler


@pytest.fixture(autouse=True)
def _clean_scheduler():
    scheduler.shutdown()
    yield
    scheduler.shutdown()


def test_start_registers_sync_and_notification_jobs():
    instance = scheduler.start()

    assert {job.id for job in instance.get_jobs()} == {"strava_sync", "due_notifications"}


def test_notification_job_interval_is_env_configurable(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHECK_INTERVAL_MINUTES", "15")

    instance = scheduler.start()

    job = instance.get_job("due_notifications")
    assert job.trigger.interval.total_seconds() == 15 * 60


def test_notification_job_runs_the_due_check(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler.notification_service, "check_due_schedules", lambda: calls.append(1))

    scheduler._run_notification_job()

    assert calls == [1]


def test_notification_job_swallows_and_logs_failures(monkeypatch):
    def boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(scheduler.notification_service, "check_due_schedules", boom)

    scheduler._run_notification_job()  # must not raise
