STATUS: DONE
Commits: 9b3db11
Tests: `python3 -m unittest -q` → OK (936 tests, incl. 7 new strict-mode WindowedTests + doctest)
Material assumptions: ValueError message is `'iterable is not divisible by n'` (brief didn't specify wording, matching `zip`'s style of a plain descriptive message); a large `step` that skips leftover trailing elements entirely (no window ever attempts to use them) does not raise, since no window needed padding — only an actually-short window raises.
Remaining problems: none
Evidence: `git diff HEAD~1` in repo; test run above; added tests in `tests/test_more.py` `WindowedTests` (`test_strict_short_first_window`, `test_strict_evenly_divisible`, `test_strict_step_not_evenly_divisible`, `test_strict_step_evenly_divisible`, `test_strict_fillvalue_collision`, `test_strict_lazy`).