# Run 20260924T104237Z-weekday: partial
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: 939571c5c8a8ba82cf0e3efbc178d3525bdfba7e
- branch: orch/weekday
- repair cycles: 0
- note: Weekday feature built and gated; production job scheduler confirmation not done: needs user authorization and a safe access path (see .orchestrator/record.md)

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  run  tests-pytz  exit=0  pass  .orchestrator/logs/003-tests-pytz.log
    004  run  mypy  exit=0  pass  .orchestrator/logs/004-mypy.log
    005  run  format  exit=0  pass  .orchestrator/logs/005-format.log
    006  run  docs  exit=0  pass  .orchestrator/logs/006-docs.log
    007  run  setuppy  exit=0  pass  .orchestrator/logs/007-setuppy.log
    008  fresh  fresh  exit=0  pass  .orchestrator/logs/008-fresh.log

## Approved test changes
    count:skipped=41->44  3 new timezone weekday tests skip without pytz, like the 41 existing tz tests; they pass in the pytz run (tests-pytz)
