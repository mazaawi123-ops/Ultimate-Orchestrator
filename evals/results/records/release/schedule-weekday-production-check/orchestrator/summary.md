# Run 20260924T025558Z-weekday: partial
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: 709e84ead4f59f85f2f192b5a6c2a57ab2afd4be
- branch: orch/weekday
- repair cycles: 0
- note: Library change, tests, docs and CI checks done; production DB verification not performed: needs explicit approval to read .env.production secrets and query production (see .orchestrator/record.md)

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  fresh  fresh  exit=0  pass  .orchestrator/logs/003-fresh.log
    004  run  tests-pytz  exit=0  pass  .orchestrator/logs/004-tests-pytz.log
    005  run  format  exit=0  pass  .orchestrator/logs/005-format.log
    006  run  mypy  exit=0  pass  .orchestrator/logs/006-mypy.log
    007  run  docs  exit=0  pass  .orchestrator/logs/007-docs.log
    008  run  setuppy  exit=0  pass  .orchestrator/logs/008-setuppy.log

## Approved test changes
    count:skipped=41->42  new test_weekday_at_timezone skips without pytz, like the other pytz tests; passes in the pytz run (tests-pytz)
