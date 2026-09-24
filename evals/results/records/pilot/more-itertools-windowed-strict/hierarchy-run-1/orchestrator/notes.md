# Repo notes (more-itertools)
- Layout: more_itertools/more.py (impl), more_itertools/more.pyi (type stubs, overloads), tests/test_more.py (unittest TestCase classes; WindowedTests at ~line 892).
- Docstrings are doctests: `python3 -m unittest` runs them via load_tests in tests/test_more.py, so every `>>>` example must be exact.
- Test: `python3 -m unittest -q` (930 tests, ~30s, all pass at BASE).
- Lint: `ruff format --check . && ruff check more_itertools tests && python3 -m mypy.stubtest more_itertools.more more_itertools.recipes` (all clean at BASE). Run `ruff format <file>` if format check fails.
- stubtest compares runtime signature to the .pyi: parameter names, defaults, keyword-only-ness must agree.
- Style: single quotes, 79-col lines, `raise ValueError('...')` with lowercase messages (see `windowed`'s 'n must be > 0').
- windowed() is a generator function: all errors (incl. n/step validation) surface on first next(), not at call time.
- windowed() uses a deque(maxlen=n) plus a `map(window.append, chain(iterator, padding))` trick; padding is fillvalue repeated.
- No known failing tests.
