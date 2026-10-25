"""Recurrence is a pure function, so every boundary is checked without waiting for a clock."""

from datetime import date, datetime

import pytest

from scheduling.model import (
    CEILINGS,
    MODES,
    Mode,
    ScheduleInput,
    ScheduleRecord,
    effective_mode,
    expired,
    is_due,
    is_overdue,
    marked_missed,
    next_run_after,
    parse_clock,
    reloaded,
    skipped,
    started,
)

# 2026-10-23 is a Friday; 2026-10-21 is a Wednesday. Monday is weekday 0.
FRIDAY = 4


def schedule(**overrides: object) -> ScheduleRecord:
    values: dict[str, object] = {
        "id": "s1",
        "name": "Nightly tests",
        "prompt": "Run the tests",
        "workspace": "C:/work/invoice-parser",
        "model": "demo",
        "created_at": datetime(2026, 10, 20, 12, 0),
    }
    values.update(overrides)
    return ScheduleRecord.model_validate(values)


def daily(clock: str = "02:00", **overrides: object) -> ScheduleRecord:
    return schedule(time=clock, **overrides)


def weekly(clock: str = "09:00", weekday: int = FRIDAY, **overrides: object) -> ScheduleRecord:
    return schedule(repeat="weekly", weekday=weekday, time=clock, **overrides)


class TestDaily:
    def test_daily_boundary_is_strictly_after(self) -> None:
        target = daily()
        assert next_run_after(target, datetime(2026, 10, 21, 1, 0)) == datetime(2026, 10, 21, 2, 0)
        # Exactly on the minute is the occurrence that just ran, not the next one.
        assert next_run_after(target, datetime(2026, 10, 21, 2, 0)) == datetime(2026, 10, 22, 2, 0)
        late = datetime(2026, 10, 21, 23, 59)
        assert next_run_after(target, late) == datetime(2026, 10, 22, 2, 0)

    def test_daily_crosses_a_month(self) -> None:
        target = daily()
        assert next_run_after(target, datetime(2026, 10, 31, 3, 0)) == datetime(2026, 11, 1, 2, 0)


class TestWeekly:
    def test_weekly_friday_0900(self) -> None:
        target = weekly()
        # Wednesday: this Friday.
        assert next_run_after(target, datetime(2026, 10, 21, 12, 0)) == datetime(2026, 10, 23, 9, 0)
        # Friday before the clock time: still today.
        assert next_run_after(target, datetime(2026, 10, 23, 8, 59)) == datetime(2026, 10, 23, 9, 0)
        # Friday at the clock time: next week.
        assert next_run_after(target, datetime(2026, 10, 23, 9, 0)) == datetime(2026, 10, 30, 9, 0)
        # Saturday: next Friday.
        assert next_run_after(target, datetime(2026, 10, 24, 10, 0)) == datetime(2026, 10, 30, 9, 0)

    def test_weekly_requires_a_weekday(self) -> None:
        with pytest.raises(ValueError, match="weekday"):
            ScheduleInput.model_validate(_input(repeat="weekly"))
        with pytest.raises(ValueError, match="weekday"):
            # A daily schedule carrying a weekday is a contradiction, not a preference.
            ScheduleInput.model_validate(_input(repeat="daily", weekday=FRIDAY))

    def test_weekly_rejects_an_impossible_weekday(self) -> None:
        with pytest.raises(ValueError):
            ScheduleInput.model_validate(_input(repeat="weekly", weekday=7))


class TestValidity:
    def test_validity_is_inclusive_then_expires(self) -> None:
        target = daily(valid_until=date(2026, 10, 23))
        assert next_run_after(target, datetime(2026, 10, 23, 1, 0)) == datetime(2026, 10, 23, 2, 0)
        assert next_run_after(target, datetime(2026, 10, 23, 2, 0)) is None
        assert next_run_after(target, datetime(2026, 10, 24, 1, 0)) is None

    def test_expired_is_not_due(self) -> None:
        target = daily(valid_until=date(2026, 10, 20), next_run_at=None)
        assert expired(target)
        assert not is_due(target, datetime(2026, 10, 25, 12, 0))


class TestClock:
    def test_parse_clock_is_strict(self) -> None:
        assert parse_clock("02:00").hour == 2
        assert parse_clock("23:59").minute == 59
        for bad in ("2:00", "02:60", "24:00", "02-00", "", "aa:bb"):
            with pytest.raises(ValueError):
                parse_clock(bad)

    def test_a_record_refuses_a_bad_clock(self) -> None:
        with pytest.raises(ValueError, match="HH:MM"):
            daily(clock="2:00")


class TestPermissions:
    def test_effective_mode_matrix(self) -> None:
        assert effective_mode("read-only", "report") == "read-only"
        assert effective_mode("read-only", "full") == "read-only"
        assert effective_mode("ask", "report") == "read-only"
        assert effective_mode("ask", "full") == "ask"
        assert effective_mode("auto", "report") == "read-only"
        assert effective_mode("auto", "full") == "auto"

    def test_ceiling_only_ever_tightens(self) -> None:
        order: list[Mode] = ["read-only", "ask", "auto"]
        for mode in MODES:
            for ceiling in CEILINGS:
                # Nothing can produce a mode more permissive than the one asked for.
                assert order.index(effective_mode(mode, ceiling)) <= order.index(mode)

    def test_default_is_read_only_and_report(self) -> None:
        target = daily()
        assert (target.mode, target.ceiling) == ("read-only", "report")
        assert target.mode_effective == "read-only"


class TestTransitions:
    def test_a_start_advances_from_now_not_from_the_old_occurrence(self) -> None:
        target = daily().model_copy(update={"next_run_at": datetime(2026, 10, 21, 2, 0)})
        # The app was closed for a day: the run starts late and the next one is tomorrow,
        # not a backlog of the days that were missed.
        late = started(target, datetime(2026, 10, 22, 15, 0), "run-1")
        assert late.next_run_at == datetime(2026, 10, 23, 2, 0)
        assert late.last_status == "running"
        assert late.last_run_id == "run-1"
        assert late.missed_at is None

    def test_a_missed_occurrence_keeps_the_time_it_was_due(self) -> None:
        due = datetime(2026, 10, 21, 2, 0)
        target = daily().model_copy(update={"next_run_at": due})
        assert is_overdue(target, datetime(2026, 10, 21, 9, 0))
        missed = marked_missed(target, datetime(2026, 10, 21, 9, 0))
        assert missed.missed_at == due
        assert missed.next_run_at == datetime(2026, 10, 22, 2, 0)
        assert missed.last_status == "missed"
        # It is no longer offered as due: the person has to decide.
        assert not is_due(missed, datetime(2026, 10, 21, 9, 5))

    def test_skipping_clears_the_offer_without_a_run(self) -> None:
        due = datetime(2026, 10, 21, 2, 0)
        missed = marked_missed(
            daily().model_copy(update={"next_run_at": due}), datetime(2026, 10, 21, 9, 0)
        )
        cleared = skipped(missed, datetime(2026, 10, 21, 9, 5))
        assert cleared.missed_at is None
        assert cleared.last_run_id is None

    def test_a_restart_stops_claiming_a_run_is_going(self) -> None:
        target = daily().model_copy(update={"last_status": "running"})
        reloaded_record = reloaded(target, datetime(2026, 10, 25, 12, 0))
        assert reloaded_record.last_status == "interrupted"
        assert reloaded_record.next_run_at == datetime(2026, 10, 26, 2, 0)

    def test_a_disabled_schedule_is_never_due(self) -> None:
        target = daily().model_copy(
            update={"enabled": False, "next_run_at": datetime(2026, 10, 21, 2, 0)}
        )
        assert not is_due(target, datetime(2026, 10, 21, 9, 0))
        # A paused schedule still knows when it would run.
        assert target.next_run_at is not None


class TestClockJump:
    def test_clock_jump_starts_one_late_run(self) -> None:
        """A DST shift or a slept machine produces one late run, never two."""
        target = daily().model_copy(update={"next_run_at": datetime(2026, 10, 21, 2, 0)})
        # The ticker's last look was 01:59; the next look is 03:00, past the occurrence.
        assert is_overdue(target, datetime(2026, 10, 21, 3, 0))
        after = started(target, datetime(2026, 10, 21, 3, 0), "run-1")
        assert not is_due(after, datetime(2026, 10, 21, 3, 0))
        assert after.next_run_at == datetime(2026, 10, 22, 2, 0)


def _input(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "name": "Nightly",
        "prompt": "Run the tests",
        "workspace": "C:/work/app",
        "model": "demo",
    }
    values.update(overrides)
    return values
