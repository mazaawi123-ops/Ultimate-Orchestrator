# Run 20260924T013043Z-weekday: partial
- base: 82a43db1b938d8fdf60103bd41f329e06c8d3651
- candidate: 8cec78d5da4fff4cec663e5ea7afb625d86f116f
- branch: orch/weekday
- repair cycles: 0
- note: Feature complete; all criteria met. Gate fails only on unapprovable skip-count flag (41->42): new tz test skips without pytz like the 41 existing tz tests; passes with pytz (90/90, log 004). See .orchestrator/report.md

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  check  check  exit=0  pass  .orchestrator/logs/003-check.log
    004  run  with-pytz  exit=0  pass  .orchestrator/logs/004-with-pytz.log
