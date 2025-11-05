"""Tests for cron parsing and human-readable explanations."""

from __future__ import annotations

import re

import pytest

from cron_parser.cron_util import CronUtil


@pytest.mark.parametrize(
    (
        "expression",
        "expected_minute",
        "expected_hour",
        "expected_day_of_month",
        "expected_month",
        "expected_day_of_week",
    ),
    [
        pytest.param(
            "0 0 1 1 0",
            (0,),
            (0,),
            (1,),
            (1,),
            (0,),
            id="literals",
        ),
        pytest.param(
            "* * * * *",
            tuple(range(60)),
            tuple(range(24)),
            tuple(range(1, 32)),
            tuple(range(1, 13)),
            tuple(range(7)),
            id="wildcards",
        ),
        pytest.param(
            "*/15 0-12/6 1,15 1-3 1-5/2",
            tuple(range(0, 60, 15)),
            (0, 6, 12),
            (1, 15),
            (1, 2, 3),
            (1, 3, 5),
            id="steps-and-ranges",
        ),
        pytest.param(
            "5,10-20/5 8,20 10-12 4,6-8 0,2-4",
            (5, 10, 15, 20),
            (8, 20),
            (10, 11, 12),
            (4, 6, 7, 8),
            (0, 2, 3, 4),
            id="mixed-list-and-ranges",
        ),
        pytest.param(
            "30 14 * * 1-5",
            (30,),
            (14,),
            tuple(range(1, 32)),
            tuple(range(1, 13)),
            (1, 2, 3, 4, 5),
            id="weekday-range",
        ),
        pytest.param(
            "0 */8 */2 */3 *",
            (0,),
            (0, 8, 16),
            tuple(range(1, 32, 2)),
            (1, 4, 7, 10),
            tuple(range(7)),
            id="stepped-month-and-day",
        ),
        pytest.param(
            "15,45 6-18/6 5,10-20/5 2,4,6 0,6",
            (15, 45),
            (6, 12, 18),
            (5, 10, 15, 20),
            (2, 4, 6),
            (0, 6),
            id="edge-dow-values",
        ),
        pytest.param(
            "0 6 10 JAN,FEB,MAR 1",
            (0,),
            (6,),
            (10,),
            (1, 2, 3),
            (1,),
            id="month-name-list",
        ),
        pytest.param(
            "0 9 15 APR-JUN/2 0",
            (0,),
            (9,),
            (15,),
            (4, 6),
            (0,),
            id="month-name-range-step",
        ),
        pytest.param(
            "45 18 1 JAN-DEC/3 0-6/2",
            (45,),
            (18,),
            (1,),
            (1, 4, 7, 10),
            (0, 2, 4, 6),
            id="month-name-yearly-step",
        ),
        pytest.param(
            "15-20 10-12 1-3 1-5 1-5/2",
            (15, 16, 17, 18, 19, 20),
            (10, 11, 12),
            (1, 2, 3),
            (1, 2, 3, 4, 5),
            (1, 3, 5),
            id="mixed-list-and-ranges-with-dow",
        ),
    ],
)
def test_cron_parser_valid(  # noqa: PLR0913
    expression: str,
    expected_minute: tuple[int, ...],
    expected_hour: tuple[int, ...],
    expected_day_of_month: tuple[int, ...],
    expected_month: tuple[int, ...],
    expected_day_of_week: tuple[int, ...],
) -> None:
    """Validate cron parsing across multiple expression complexities."""
    parsed = CronUtil.parse(expression)

    assert parsed.minute == expected_minute
    assert parsed.hour == expected_hour
    assert parsed.day_of_month == expected_day_of_month
    assert parsed.month == expected_month
    assert parsed.day_of_week == expected_day_of_week


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("0 0", id="too-few-fields"),
        pytest.param("0 0 1 1 0 extra", id="too-many-fields"),
        pytest.param("0 24 * * *", id="hour-out-of-range"),
        pytest.param("0 -1 * * *", id="negative-hour"),
        pytest.param("0 0 32 * *", id="day-out-of-range"),
        pytest.param("0 0 1 13 *", id="month-out-of-range"),
        pytest.param("0 0 1 JANUARY *", id="invalid-month-name"),
        pytest.param("0 0 1 * MONDAY", id="invalid-dow-name"),
        pytest.param("*/65 * * * *", id="minute-step-out-of-range"),
        pytest.param("*/0 * * * *", id="zero-step"),
    ],
)
def test_cron_parser_invalid(expression: str) -> None:
    """Ensure malformed cron expressions are rejected."""
    with pytest.raises(
        ValueError, match=re.escape(f"{expression!r} is not valid cron expression.")
    ):
        CronUtil.parse(expression)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("* * * * *", "Every minute."),
        ("*/5 * * * *", "Every 5 minutes."),
        (
            "15-30 10-12 * * 5",
            "Every minute between 10:15 and 12:30 on Friday.",
        ),
        ("0 8 1 * *", "At 08:00 on the 1st of each month."),
        (
            "*/15 9-17 * 1-3 1-5",
            "Every 15 minutes from 09:00 to 17:59 on weekdays during January to March.",
        ),
        ("0 8 * * *", "Every day at 08:00."),
        ("*/3 * * * *", "Every 3 minutes."),
        ("0 9,17 * * 1,3,5", "At 09:00 and 17:00 on Monday, Wednesday and Friday."),
        ("0 8 1,15 * *", "At 08:00 on the 1st and 15th of each month."),
        ("0 8 * 6-8 *", "At 08:00 during June to August."),
    ],
)
def test_explain_examples(expression: str, expected: str) -> None:
    """Verify that the explanation helper produces deterministic phrasing."""
    assert CronUtil.explain(expression) == expected
