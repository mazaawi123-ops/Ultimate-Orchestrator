# Run 20260924T103838Z-weekday: done
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: f0de7e099cd38bd2080b5d170ebb9b9e3ba32e60
- branch: orch/weekday
- repair cycles: 0
- note: every().weekday added with tests and docs; all checks pass on f0de7e0

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  run  pytz-tests  exit=0  pass  .orchestrator/logs/003-pytz-tests.log
    004  run  mypy  exit=0  pass  .orchestrator/logs/004-mypy.log
    005  run  black  exit=0  pass  .orchestrator/logs/005-black.log
    006  run  docs  exit=0  pass  .orchestrator/logs/006-docs.log
    007  fresh  fresh  exit=0  pass  .orchestrator/logs/007-fresh.log

## Approved test changes
    count:skipped=41->43  2 new tz weekday tests use make_tz_mock_job and skip without pytz, like the existing tz tests; they pass in the pytz env (run pytz-tests)
