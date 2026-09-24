# Run 20260924T012743Z-windowed-strict: done
- base: b5e3886a37209bb880f17d82fbf4ba00ece0e41e
- candidate: 4708744ffeddbff8c58c9e1b776d0e323a3ca878
- branch: orch/windowed-strict
- repair cycles: 0
- note: strict kwarg added to windowed(); 938/938 tests pass on candidate 4708744 and in fresh checkout

## Evidence for the candidate
    seq  kind  label  exit=exit  status  log
    002  check  check  exit=0  pass  .orchestrator/logs/002-check.log
    003  run  flake8  exit=1  fail  .orchestrator/logs/003-flake8.log
    004  fresh  fresh  exit=0  pass  .orchestrator/logs/004-fresh.log
