"""Expand five-field cron expressions into explicit integer schedules."""

import asyncio
from typing import Final

from cron_parser.common import DAY_NAME_TO_INDEX, FIELD_RANGES, MONTH_NAME_TO_INDEX, CronSchedule

EXPECTED_FIELD_COUNT: Final[int] = 5


async def async_parse(expression: str) -> CronSchedule:
    """Asynchronous version of :func:`parse`."""
    return await asyncio.to_thread(parse, expression)


def parse(expression: str) -> CronSchedule:
    """Parse a cron expression into explicit field values.

    The parser expects the traditional five-field format: minute, hour,
    day of month, month, and day of week. Each field supports single
    values, ranges, steps (``*/n``), and comma-separated lists.

    :param expression: Raw cron expression using space-separated fields.
    :returns: A :class:`CronSchedule` with sorted integer values per field.
    :raises ValueError: If the expression has invalid syntax or values.
    """
    expression_parts = expression.split()
    if len(expression_parts) != EXPECTED_FIELD_COUNT:
        raise _invalid_cron_expression(expression)

    minutes, hours, day_of_month, month, day_of_week = expression_parts
    try:
        return CronSchedule(
            minute=_parse_expression(minutes, FIELD_RANGES["minutes"]),
            hour=_parse_expression(hours, FIELD_RANGES["hours"]),
            day_of_month=_parse_expression(day_of_month, FIELD_RANGES["day_of_month"]),
            month=_parse_expression(
                month, FIELD_RANGES["month"], transform_map=MONTH_NAME_TO_INDEX
            ),
            day_of_week=_parse_expression(
                day_of_week, FIELD_RANGES["day_of_week"], transform_map=DAY_NAME_TO_INDEX
            ),
        )
    except ValueError as exc:
        raise _invalid_cron_expression(expression) from exc


def _parse_expression(
    expr: str, allowed: tuple[int, ...], transform_map: dict[str, int] | None = None
) -> tuple[int, ...]:
    """Expand a comma-delimited cron field into explicit integers.

    :param expr: Portion of the cron expression representing one field.
    :param allowed: Sorted tuple with every value allowed for this field.
    :param transform_map: Optional mapping for aliases such as month names.
    :returns: Sorted tuple of integers derived from the expression.
    :raises ValueError: If the field contains an invalid token.
    """
    parts = expr.split(",")
    result = set()
    try:
        for part in parts:
            values = _parse_part(part, allowed, transform_map)
            result.update(values)
    except ValueError as exc:
        raise _invalid_cron_expression(expr) from exc

    return tuple(sorted(result))


def _parse_part(
    part: str, allowed: tuple[int, ...], transform_map: dict[str, int] | None = None
) -> tuple[int, ...]:
    """Interpret a single cron token.

    :param part: Token such as ``"1-5"`` or ``"*/15"``.
    :param allowed: Sorted tuple with allowed values for validation.
    :param transform_map: Optional symbolic alias map (e.g. ``"JAN": 1``).
    :returns: Tuple of integers represented by the token.
    :raises ValueError: If the token cannot be transformed into values.
    """
    transform_map = transform_map or {}
    value_expr, step_expr = _expr_to_parts(part)

    if step_expr >= len(allowed):
        raise _invalid_cron_expression(part)

    if value_expr in transform_map:
        value_expr = str(transform_map[value_expr])

    if value_expr.isdigit():
        if step_expr != 1:
            raise _invalid_cron_expression(part)
        if int(value_expr) not in allowed:
            raise _invalid_cron_expression(part)
        return (int(value_expr),)

    if value_expr == "*":
        return tuple(range(allowed[0], allowed[-1] + 1, step_expr))

    if "-" in value_expr:
        start, end = value_expr.split("-")
        if start in transform_map:
            start = str(transform_map[start])
        if end in transform_map:
            end = str(transform_map[end])
        start, end = int(start), int(end)
        if start not in allowed or end not in allowed:
            raise _invalid_cron_expression(part)
        return tuple(range(start, end + 1, step_expr))

    raise _invalid_cron_expression(part)


def _invalid_cron_expression(expr: str) -> ValueError:
    """Build a standardised :class:`ValueError` for invalid cron input.

    :param expr: Raw expression fragment that failed validation.
    :returns: A ``ValueError`` instance ready to be raised.
    """
    return ValueError(f"{expr!r} is not valid cron expression.")


def _expr_to_parts(expr: str) -> tuple[str, int]:
    """Split a cron token into its base expression and step.

    :param expr: Cron token that may contain a ``/`` step indicator.
    :returns: Tuple of the base expression and integer step.
    :raises ValueError: If the step component is not a valid integer.
    """
    if "/" in expr:
        value_expr, step_expr = expr.split("/")
        if not step_expr.isdigit():
            raise _invalid_cron_expression(expr)
        step_expr = int(step_expr)
    else:
        value_expr, step_expr = expr, 1

    return value_expr, step_expr
