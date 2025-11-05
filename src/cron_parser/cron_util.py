"""Cron expression parser utilities.

The module exposes :class:`CronUtil` that expands a five-field cron
expression into explicit integer values and can summarise schedules
in plain language.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cron_parser.explain import async_explain, explain
from cron_parser.parse import async_parse, parse

if TYPE_CHECKING:
    from cron_parser.common import CronSchedule


class CronUtil:
    """Entry point for parsing and explaining cron expressions.

    The class exposes class methods so it can be used without instantiation.
    """

    @classmethod
    def parse(cls, expression: str) -> CronSchedule:
        """Parse a cron expression into explicit field values.

        The parser expects the traditional five-field format: minute, hour,
        day of month, month, and day of week. Each field supports single
        values, ranges, steps (``*/n``), and comma-separated lists.

        :param expression: Raw cron expression using space-separated fields.
        :returns: A :class:`CronSchedule` with sorted integer values per field.
        :raises ValueError: If the expression has invalid syntax or values.
        """
        return parse(expression)

    @classmethod
    async def parse_async(cls, expression: str) -> CronSchedule:
        """Asynchronous version of :func:`parse`."""
        return await async_parse(expression)

    @classmethod
    def explain(cls, spec: str | CronSchedule) -> str:
        """Explain a cron expression in plain English."""
        return explain(spec)

    @classmethod
    async def async_explain(cls, spec: str | CronSchedule) -> str:
        """Asynchronous version of :meth:`explain`."""
        return await async_explain(spec)
