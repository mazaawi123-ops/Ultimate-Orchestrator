# Run 20260924T093013Z-weekday: done
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: 22f1204428a95e12e8b1092efe02b0b5f5fa7c9d
- branch: orch/weekday
- repair cycles: 1
- note: every().weekday added; Mon-Fri only incl. late/run_all weekend skip; reviewed + 1 repair; all CI checks pass on 22f1204

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    012  check  check  exit=0  pass  .orchestrator/logs/012-check.log
    013  run  format  exit=0  pass  .orchestrator/logs/013-format.log
    014  run  mypy  exit=0  pass  .orchestrator/logs/014-mypy.log
    015  run  pytz-tests  exit=0  pass  .orchestrator/logs/015-pytz-tests.log
    016  run  docs  exit=0  pass  .orchestrator/logs/016-docs.log
    017  fresh  fresh  exit=0  pass  .orchestrator/logs/017-fresh.log
    018  review-diff  diff  exit=0  pass  .orchestrator/review/candidate-22f1204428a9.patch
    019  recheck  review  exit=-  pass  

## Approved test changes
    count:skipped=41->42  new test_tz_weekday skips without pytz, like the other tz tests; it passes in the pytz env (check pytz-tests)
    count:skipped=41->43  new test_tz_weekday and test_tz_weekday_after_spring_forward_weekend skip without pytz, like the other tz tests; both pass in the pytz env (pytz-tests 92/92)
