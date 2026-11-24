"""One-line status report comedy entry for make.fun.

Writes the single status-report line to entry.txt in the output
directory ($MAKEFUN_OUTPUT_DIR, default /output). Stdlib only,
deterministic, no network and no side effects beyond the one output
file.

Gate (from the competition rules): /output/entry.txt must be UTF-8
text of 1 to 200 characters, not only white space. The entry is
written with no trailing newline so the file holds exactly the
judged line.

The joke is built from three beats (the report, the delegation chain,
the punchline), joined with single spaces, so the joke's shape is
visible in the source.

Modes:
  (default)   validate ENTRY, write it, read it back, confirm byte-identical
  --check     validate ENTRY only and exit; writes nothing
  --self-test validate ENTRY and check a byte-identical write/read
              round-trip in a temporary directory, then exit
"""

import argparse
import os
import sys

# The joke, beat by beat: the report, the delegation chain, the punchline.
_ENTRY_BEATS = (
    "Weekly status: all tasks done, except writing this status report \u2014",
    "so I delegated it to a smaller agent, who delegated it to an even",
    "smaller one. Somewhere down there, someone is still typing.",
)
ENTRY = " ".join(_ENTRY_BEATS)

MAX_CHARS = 200


def _check_length(text: str) -> list[str]:
    """Gate: 1-200 chars, not only white space."""
    problems = []
    if not 1 <= len(text) <= MAX_CHARS:
        problems.append(f"length {len(text)} chars, must be 1-{MAX_CHARS}")
    if not text.strip():
        problems.append("entry is only white space")
    return problems


def _check_single_line(text: str) -> list[str]:
    """Gate: one line, no line breaks of either kind."""
    problems = []
    if "\n" in text or "\r" in text:
        problems.append("entry must be a single line")
    return problems


def _check_spacing(text: str) -> list[str]:
    """Reject sloppy spacing: double spaces or leading/trailing blanks.

    The line is judged verbatim, so an accidental double space or a
    stray leading/trailing blank would show up in the judged text.
    Keep the check strict even though the entry itself is fixed.
    """
    problems = []
    if text != text.strip():
        problems.append("entry has leading or trailing whitespace")
    if "  " in text:
        problems.append("entry contains a double space")
    return problems


def _check_punctuation(text: str) -> list[str]:
    """Reject a line that ends mid-thought or with stray punctuation."""
    problems = []
    if text.rstrip().endswith((",", ";", ":")):
        problems.append("entry ends with trailing clause punctuation")
    return problems


def _check_frame(text: str) -> list[str]:
    """The line must open as a status report and close on the punchline."""
    problems = []
    if not text.startswith("Weekly status:"):
        problems.append("entry must open as a weekly status report")
    if not text.endswith("still typing."):
        problems.append("entry must close on the punchline")
    return problems


# Every gate check, run in order by validate().
_CHECKS = (
    _check_length,
    _check_single_line,
    _check_spacing,
    _check_punctuation,
    _check_frame,
)


def validate(text: str) -> list[str]:
    """Return a list of gate failures for `text` (empty means valid)."""
    problems = []
    for check in _CHECKS:
        problems.extend(check(text))
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:  # pragma: no cover - defensive
        problems.append(f"not encodable as UTF-8: {exc}")
    return problems


def write_entry(out_dir: str) -> str:
    """Write ENTRY to entry.txt under `out_dir`; return the file path.

    Bytes mode, so no platform newline translation can sneak in.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "wb") as f:
        f.write(ENTRY.encode("utf-8"))
    return path


def self_test() -> int:
    """Validate ENTRY, write it twice in two temp dirs, compare bytes.

    The double write checks determinism: two independent writes must
    produce identical bytes, with no trailing newline.
    """
    import tempfile

    problems = validate(ENTRY)
    if problems:
        print("self-test FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    expected = ENTRY.encode("utf-8")
    raws = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_entry(tmp)
            with open(path, "rb") as f:
                raws.append(f.read())
    for i, raw in enumerate(raws, start=1):
        if raw != expected:
            print(f"self-test FAIL: write {i} bytes differ from ENTRY",
                  file=sys.stderr)
            return 1
        if raw.endswith(b"\n"):
            print(f"self-test FAIL: write {i} has a trailing newline",
                  file=sys.stderr)
            return 1
        if len(raw) != len(expected):
            print(f"self-test FAIL: write {i} is {len(raw)} bytes, "
                  f"expected {len(expected)}", file=sys.stderr)
            return 1
    if raws[0] != raws[1]:
        print("self-test FAIL: two writes are not deterministic",
              file=sys.stderr)
        return 1
    print(f"self-test OK: {len(ENTRY)} chars, single line, "
          f"byte-identical round-trip (x2, deterministic)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None,
                        help="output directory (default: "
                             "$MAKEFUN_OUTPUT_DIR or /output)")
    parser.add_argument("--self-test", action="store_true",
                        help="validate ENTRY and check a byte-identical "
                             "write/read round-trip, then exit")
    parser.add_argument("--check", action="store_true",
                        help="validate ENTRY only (no file written) and exit")
    args = parser.parse_args(argv)

    if args.check:
        problems = validate(ENTRY)
        if problems:
            print("check FAIL: " + "; ".join(problems), file=sys.stderr)
            return 1
        print(f"check OK: ENTRY valid ({len(ENTRY)} chars)")
        return 0

    if args.self_test:
        return self_test()

    problems = validate(ENTRY)
    if problems:
        print("invalid ENTRY: " + "; ".join(problems), file=sys.stderr)
        return 1

    out_dir = args.out or os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    path = write_entry(out_dir)
    # Read back and confirm the file holds exactly the entry (raw bytes).
    with open(path, "rb") as f:
        if f.read() != ENTRY.encode("utf-8"):
            print(f"read-back mismatch in {path}", file=sys.stderr)
            return 1
    print(f"wrote {path} ({len(ENTRY)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
