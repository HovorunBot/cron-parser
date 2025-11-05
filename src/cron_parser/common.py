"""Shared constants and lightweight types used across cron utilities.

Day-of-week values use the cron convention where 0 represents Sunday and 6
represents Saturday.
"""

from typing import NamedTuple

FIELD_RANGES = {
    "minutes": tuple(range(60)),
    "hours": tuple(range(24)),
    "day_of_month": tuple(range(1, 32)),
    "month": tuple(range(1, 13)),
    "day_of_week": tuple(range(7)),
}

DAY_NAME_TO_INDEX = {"SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6}
MONTH_NAME_TO_INDEX = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

DAY_INDEX_TO_NAME = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}

MONTH_INDEX_TO_NAME = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


class CronSchedule(NamedTuple):
    """Structured representation of the five cron fields.

    Each attribute contains a tuple of integer values that represent the
    concrete schedule derived from the raw cron expression.
    """

    minute: tuple[int, ...]
    hour: tuple[int, ...]
    day_of_month: tuple[int, ...]
    month: tuple[int, ...]
    day_of_week: tuple[int, ...]

    @property
    def dom(self) -> tuple[int, ...]:
        """Alias for ``day_of_month`` property."""
        return self.day_of_month

    @property
    def dow(self) -> tuple[int, ...]:
        """Alias for ``day_of_week`` property."""
        return self.day_of_week
