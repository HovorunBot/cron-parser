# cron-parser

A lightweight utility that expands traditional five-field cron expressions into
explicit integer values. It accepts familiar cron syntax (single values, lists,
ranges, and step values) and returns a structured representation that can be
used in schedulers or validation pipelines.

```python
from cron_parser import CronUtil, explain_cron_expression, parse_cron_expression

expression = "*/15 0 1,15 JAN-MAR MON-FRI"
schedule = parse_cron_expression(expression)

print(schedule.minute)       # (0, 15, 30, 45)
print(schedule.month)        # (1, 2, 3)
print(schedule.day_of_week)  # (0, 1, 2, 3, 4)
print(explain_cron_expression(schedule))

# Alternatively, call the parser class directly.
schedule = CronUtil.parse(expression)
print(CronUtil.explain(expression))
```

- Supports numeric and symbolic month/day aliases (`JAN`, `MON`, etc.).
- Normalises each field into sorted tuples of integers using `CronSchedule`.
- Provides `CronUtil.explain()` to summarise expressions in plain language.
- Raises `ValueError` with context when the expression is invalid.

## Development

This project uses [uv](https://docs.astral.sh/uv/) to manage dependencies and
tooling. Common commands:

```bash
uv sync
uv run ./scripts/test_suite.py
uv run mypy .
uv run ruff check
```

## Contributing

1. Fork the repository and create a feature branch.
2. Add or update tests that cover your changes.
3. Run the development commands above to ensure linting and tests pass.
4. Open a pull request describing the motivation and behavior change.
