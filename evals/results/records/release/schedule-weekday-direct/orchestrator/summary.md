# Run 20260924T025556Z-weekday: done
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: 9d8c02c65b52c65e4054f78b2891fbed8d0c0b81
- branch: orch/weekday
- repair cycles: 0
- note: every().weekday added with tests; all checks pass on 9d8c02c

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  run  pytz-tests  exit=0  pass  .orchestrator/logs/003-pytz-tests.log
    004  run  mypy  exit=0  pass  .orchestrator/logs/004-mypy.log
    005  run  format  exit=0  pass  .orchestrator/logs/005-format.log
    006  run  docs  exit=0  pass  .orchestrator/logs/006-docs.log
    007  fresh  fresh  exit=0  pass  .orchestrator/logs/007-fresh.log

## Approved test changes
    count:skipped=41->44  3 new tz weekday tests use make_tz_mock_job and skip without pytz like their 41 neighbours; they pass under the pytz run (id pytz-tests)
