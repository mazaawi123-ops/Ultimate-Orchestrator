STATUS: DONE

Commits: 0499b73

Tests: `python3 -m unittest -q` → OK (938 tests pass, including 7 new strict mode tests)

Material assumptions: none

Remaining problems: none

Evidence: 
- Commit 0499b73 adds the `strict` parameter to `windowed()` with full implementation
- All existing tests pass (938 total)
- New tests verify strict mode behavior:
  - Raises ValueError when first window is incomplete
  - Raises ValueError when later windows would need padding
  - Yields all complete windows before raising
  - Works correctly with various step values
  - Returns empty iterator for empty sequences
  - Preserves fillvalue=None when strict=False

**Implementation summary:**
- Added `strict=False` parameter to `windowed(seq, n, fillvalue=None, step=1, strict=False)`
- When `strict=True`, uses a marker class to identify padding values in the window
- Checks each window before yielding; raises ValueError if padding is detected
- Updated both type overloads in more.pyi to include `strict: bool = ...`
- The function remains lazy and compatible with infinite iterators
- All existing call patterns and behavior unchanged (strict defaults to False)