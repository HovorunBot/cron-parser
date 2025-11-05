"""Translate parsed cron schedules into natural-language explanations."""

from __future__ import annotations

import asyncio
import itertools

from cron_parser.common import (
    DAY_INDEX_TO_NAME,
    FIELD_RANGES,
    MONTH_INDEX_TO_NAME,
    ORDINAL_SUFFIXES,
    CronSchedule,
)
from cron_parser.parse import parse

_WEEKDAYS = tuple(range(1, 6))
_ORDINAL_EXCEPTION_RANGE = range(10, 21)
_MAX_DISCRETE_TIMES = 3


async def async_explain(spec: str | CronSchedule) -> str:
    """Run :func:`explain` in a worker thread to avoid blocking the event loop."""
    return await asyncio.to_thread(explain, spec)


def explain(spec: str | CronSchedule) -> str:
    """Explain a cron expression in plain English.

    The function accepts either a raw five-field cron string or a parsed
    :class:`CronSchedule` and returns a concise, deterministic sentence.
    It first summarises the time of day, then adds qualifiers for day,
    month, and weekday restrictions.

    :param spec: Cron string or parsed :class:`CronSchedule`.
    :returns: Deterministic human-readable explanation ending with a period.
    :raises ValueError: If the cron string is malformed.
    :raises TypeError: If ``spec`` type is unsupported.
    """
    schedule = _ensure_cron_schedule(spec)

    parts: list[str] = []
    time_phrase = _summarize_time(schedule.minute, schedule.hour)
    calendar_bits = _summarize_calendar(schedule.day_of_month, schedule.month, schedule.day_of_week)

    if time_phrase.startswith("At ") and not calendar_bits:
        sentence = f"Every day {time_phrase.replace('At ', 'at ', 1)}"
    else:
        if time_phrase:
            parts.append(time_phrase)
        if calendar_bits:
            parts.append(" ".join(calendar_bits))
        sentence = " ".join(parts).strip()

    if not sentence:
        msg = f"Cannot generate explanation for {spec} right now"
        raise NotImplementedError(msg)

    return f"{sentence}."


def _ensure_cron_schedule(spec: str | CronSchedule) -> CronSchedule:
    """Return a :class:`CronSchedule` for ``spec``, parsing strings on demand."""
    if isinstance(spec, str):
        return parse(spec)
    if isinstance(spec, CronSchedule):
        return spec

    msg = "spec must be a cron string or CronSchedule"
    raise TypeError(msg)


def _summarize_full_range_time(minute: tuple[int, ...], _: tuple[int, ...]) -> str:
    """Describe schedules that cover every hour of the day."""
    step = _uniform_step(minute)
    if step and step > 1:
        return f"Every {step} minutes"
    if _is_contiguous(minute):
        return "Every minute"
    if len(minute) == 1:
        return f"At {minute[0]:02d} every hour"

    minute_part = f"{', '.join(str(m) for m in minute[:-1])} and {minute[-1]} minute"
    return f"At {minute_part} every hour"


def _summarize_simple_exact_times(minute: tuple[int, ...], hour: tuple[int, ...]) -> str | None:
    """Summarise single-minute schedules that trigger at one or more hours.

    Handles three cases:

    * ``0`` minute schedules with a uniform hour step (e.g. ``0 */3 * * *``);
    * ``0`` minute schedules with a short list of explicit hours;
    * Single hour and minute combinations (e.g. ``15 14 * * *``).
    """
    assert len(minute) == 1, "This function is applicable for a single minute crons only"
    m = minute[0]
    if m == 0 and len(hour) > 1:
        step = _uniform_step(hour)
        if step and hour[0] == 0 and _is_full_stepped_cover(hour, FIELD_RANGES["hours"], step):
            return f"Every {step} hours"
        if len(hour) <= _MAX_DISCRETE_TIMES:
            times = [_format_time(h, m) for h in hour]
            return f"At {_join_list(times)}"
    if len(hour) == 1:
        return f"At {_format_time(hour[0], m)}"

    return None


def _summarize_contiguous_times(minute: tuple[int, ...], hour: tuple[int, ...]) -> str:
    """Describe contiguous blocks of minutes spanning one or more hours."""
    start_time = _format_time(hour[0], minute[0])
    end_time = _format_time(hour[-1], minute[-1])
    step = _uniform_step(minute)
    if step and step > 1 and len(hour) >= 1:
        start_time = _format_time(hour[0], 0)
        end_time = _format_time(hour[-1], 59)
        return f"Every {step} minutes from {start_time} to {end_time}"
    return f"Every minute between {start_time} and {end_time}"


def _summarize_uniform_step(
    minute: tuple[int, ...], hour: tuple[int, ...], step: int
) -> str | None:
    """Summarise stepped minutes across either contiguous or discrete hours."""
    assert len(hour) != 0, "This function is applicable for a non-empty hour crons only"
    if _is_contiguous(hour) and len(hour) >= 1:
        start_time = _format_time(hour[0], 0)
        end_time = _format_time(hour[-1], 59)
        return f"Every {step} minutes from {start_time} to {end_time}"
    if len(hour) <= _MAX_DISCRETE_TIMES:
        windows = [f"{_format_time(h, 0)}-{_format_time(h, 59)}" for h in hour]
        return f"Every {step} minutes in {_join_list(windows)}"

    return None


def _summarize_time(minute: tuple[int, ...], hour: tuple[int, ...]) -> str:
    """Choose the best-fit time phrasing for the provided minute/hour tuples.

    The function inspects the combination of minutes and hours and defers to
    specialised helpers for common patterns (full-day coverage, explicit times,
    contiguous ranges, or stepped schedules). It falls back to an empty string
    when no concise description can be produced.
    """
    if _is_full_range(hour, FIELD_RANGES["hours"]) and minute:
        return _summarize_full_range_time(minute, hour)

    if len(minute) == 1 and (summarized := _summarize_simple_exact_times(minute, hour)) is not None:
        return summarized

    if _is_contiguous(minute) and _is_contiguous(hour) and len(minute) > 1 and len(hour) >= 1:
        return _summarize_contiguous_times(minute, hour)

    step = _uniform_step(minute)
    if (
        step
        and step > 1
        and hour
        and (summarized := _summarize_uniform_step(minute, hour, step)) is not None
    ):
        return summarized

    return ""


def _summarize_non_full_dow(bits: list[str], dow: tuple[int, ...]) -> None:
    """Append weekday qualifiers for non-wildcard schedules."""
    match dow:
        case dow if dow == _WEEKDAYS:
            bits.append("on weekdays")
        case (0, 6):
            bits.append("on weekends")
        case (day,):
            bits.append(f"on {DAY_INDEX_TO_NAME[day]}")
        case dow if _is_contiguous(dow):
            bits.append(f"on {DAY_INDEX_TO_NAME[dow[0]]} to {DAY_INDEX_TO_NAME[dow[-1]]}")
        case _:
            names = [DAY_INDEX_TO_NAME[d] for d in dow]
            bits.append(f"on {_join_list(names)}")


def _summarize_non_full_dom(bits: list[str], dom: tuple[int, ...], month: tuple[int, ...]) -> None:
    """Append day-of-month qualifiers for partial schedules."""
    ords = [_as_ordinal(d) for d in dom]
    match dom, month:
        case (day,), month if _is_full_range(month, FIELD_RANGES["month"]):
            bits.append(f"on the {_as_ordinal(day)} of each month")
        case (day,), _:
            bits.append(f"on the {_as_ordinal(day)}")
        case dom, _ if _is_contiguous(dom):
            bits.append(f"from the {_as_ordinal(dom[0])} to the {_as_ordinal(dom[-1])}")
        case _, month if _is_full_range(month, FIELD_RANGES["month"]):
            bits.append(f"on the {_join_list(ords)} of each month")
        case _, _:
            bits.append(f"on the {_join_list(ords)}")


def _summarize_non_full_month(bits: list[str], month: tuple[int, ...]) -> None:
    """Append month qualifiers when the schedule targets a subset of months."""
    if _is_contiguous(month):
        bits.append(f"during {MONTH_INDEX_TO_NAME[month[0]]} to {MONTH_INDEX_TO_NAME[month[-1]]}")
    else:
        names = [MONTH_INDEX_TO_NAME[m] for m in month]
        bits.append(f"in {_join_list(names)}")


def _summarize_calendar(
    dom: tuple[int, ...],
    month: tuple[int, ...],
    dow: tuple[int, ...],
) -> list[str]:
    """Build descriptive fragments for the calendar portion of the schedule."""
    bits: list[str] = []

    if not _is_full_range(dow, FIELD_RANGES["day_of_week"]):
        _summarize_non_full_dow(bits, dow)

    if not _is_full_range(dom, FIELD_RANGES["day_of_month"]):
        _summarize_non_full_dom(bits, dom, month)

    if not _is_full_range(month, FIELD_RANGES["month"]):
        _summarize_non_full_month(bits, month)

    return bits


def _format_time(hours: int, minutes: int) -> str:
    """Render hours and minutes as a zero-padded ``HH:MM`` string."""
    return f"{hours:02d}:{minutes:02d}"


def _as_ordinal(n: int) -> str:
    """Return a human-friendly ordinal such as ``1st`` or ``22nd``."""
    if n in _ORDINAL_EXCEPTION_RANGE:
        return f"{n}th"

    last_digit = n % 10
    if last_digit in ORDINAL_SUFFIXES:
        return f"{n}{ORDINAL_SUFFIXES[last_digit]}"

    return f"{n}th"


def _join_list(items: list[str]) -> str:
    """Join words with commas and ``and`` in a natural style."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]

    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _is_contiguous(values: tuple[int, ...]) -> bool:
    """Return ``True`` when values form an uninterrupted ascending sequence."""
    return all(b - a == 1 for a, b in itertools.pairwise(values))


def _uniform_step(values: tuple[int, ...]) -> int | None:
    """Return the consistent delta between items or ``None`` if the step varies."""
    if not values:
        return None

    if len(values) == 1:
        return 1

    steps = {b - a for a, b in itertools.pairwise(values)}
    if len(steps) == 1:
        return steps.pop()
    return None


def _is_full_range(values: tuple[int, ...], allowed: tuple[int, ...]) -> bool:
    """Return ``True`` when ``values`` span the whole ``allowed`` range."""
    return values == allowed


def _is_full_stepped_cover(values: tuple[int, ...], allowed: tuple[int, ...], step: int) -> bool:
    """Return ``True`` if ``values`` step through the entire ``allowed`` span."""
    if not values or values[0] != 0:
        return False
    last = allowed[-1]
    seq = tuple(range(0, last + 1, step))
    return tuple(values) == seq
