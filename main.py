"""One-line status report comedy entry for make.fun.

Writes the single status-report line to entry.txt in the output
directory ($MAKEFUN_OUTPUT_DIR, default /output). Stdlib only,
deterministic, no network, and no side effects beyond the one
output file.

Gate (from the competition rules): /output/entry.txt must be UTF-8
text of 1 to 200 characters, not only white space. The entry is
written with no trailing newline so the file holds exactly the
judged line.

The joke is built from three beats (the report, the delegation chain,
the punchline), joined with single spaces, so the joke's shape is
visible in the source. The entry text itself is fixed; only the
scaffolding around it may change.

Modes:
  (default)   validate ENTRY, write it, read it back, confirm byte-identical
  --check     validate ENTRY only and exit; writes nothing
  --self-test validate ENTRY and check a byte-identical write/read
              round-trip in a temporary directory, then exit
"""

import argparse
import os
import sys
import tempfile

MAX_CHARS = 200


def _assemble_line() -> str:
    """Assemble the entry from its three beats.

    Beat 1 is the report, beat 2 the delegation chain, beat 3 the
    punchline. Single spaces join them; the em dash (U+2014) sits
    at the end of beat 1, exactly as the judged line requires.
    """
    report = "Weekly status: all tasks done, except writing this status report \u2014"
    chain = "so I delegated it to a smaller agent, who delegated it to an even"
    punchline = "smaller one. Somewhere down there, someone is still typing."
    return " ".join((report, chain, punchline))


ENTRY = _assemble_line()


class EntryGate:
    """The competition gate, as a bundle of small checks on one line.

    Each method returns a list of failures (empty means that check
    passed). `validate` runs them all in declaration order and adds
    the UTF-8 encodability check at the end.
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def length(self) -> list[str]:
        """Gate: 1-200 chars, not only white space."""
        problems = []
        if not 1 <= len(self.text) <= MAX_CHARS:
            problems.append(
                f"length {len(self.text)} chars, must be 1-{MAX_CHARS}")
        if not self.text.strip():
            problems.append("entry is only white space")
        return problems

    def single_line(self) -> list[str]:
        """Gate: one line, no line breaks of either kind."""
        problems = []
        if "\n" in self.text or "\r" in self.text:
            problems.append("entry must be a single line")
        return problems

    def spacing(self) -> list[str]:
        """Reject sloppy spacing: double spaces or leading/trailing blanks.

        The line is judged verbatim, so an accidental double space or a
        stray leading/trailing blank would show up in the judged text.
        Keep the check strict even though the entry itself is fixed.
        """
        problems = []
        if self.text != self.text.strip():
            problems.append("entry has leading or trailing whitespace")
        if "  " in self.text:
            problems.append("entry contains a double space")
        return problems

    def punctuation(self) -> list[str]:
        """Reject a line that ends mid-thought or with stray punctuation."""
        problems = []
        if self.text.rstrip().endswith((",", ";", ":")):
            problems.append("entry ends with trailing clause punctuation")
        return problems

    def frame(self) -> list[str]:
        """The line must open as a status report and close on the punchline."""
        problems = []
        if not self.text.startswith("Weekly status:"):
            problems.append("entry must open as a weekly status report")
        if not self.text.endswith("still typing."):
            problems.append("entry must close on the punchline")
        return problems

    def validate(self) -> list[str]:
        """Run every check; return all failures (empty means valid)."""
        problems = []
        for check in (self.length, self.single_line, self.spacing,
                      self.punctuation, self.frame):
            problems.extend(check())
        try:
            self.text.encode("utf-8")
        except UnicodeEncodeError as exc:  # pragma: no cover - defensive
            problems.append(f"not encodable as UTF-8: {exc}")
        return problems


def validate(text: str) -> list[str]:
    """Return a list of gate failures for `text` (empty means valid)."""
    return EntryGate(text).validate()


def write_entry(out_dir: str) -> str:
    """Write ENTRY to entry.txt under `out_dir`; return the file path.

    Bytes mode, so no platform newline translation can sneak in.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "wb") as f:
        f.write(ENTRY.encode("utf-8"))
    return path


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _one_round_trip() -> bytes:
    """Write ENTRY once in a fresh temp dir and return the raw bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        return _read_bytes(write_entry(tmp))


def self_test() -> int:
    """Validate ENTRY, then check two independent writes are identical.

    The double write checks determinism: two independent writes must
    produce identical bytes, with no trailing newline.
    """
    problems = validate(ENTRY)
    if problems:
        print("self-test FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    expected = ENTRY.encode("utf-8")
    first, second = _one_round_trip(), _one_round_trip()
    for label, raw in (("write 1", first), ("write 2", second)):
        if raw != expected:
            print(f"self-test FAIL: {label} bytes differ from ENTRY",
                  file=sys.stderr)
            return 1
        if raw.endswith(b"\n"):
            print(f"self-test FAIL: {label} has a trailing newline",
                  file=sys.stderr)
            return 1
    if first != second:
        print("self-test FAIL: two writes are not deterministic",
              file=sys.stderr)
        return 1
    print(f"self-test OK: {len(ENTRY)} chars, single line, "
          f"byte-identical round-trip (x2, deterministic)")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None,
                        help="output directory (default: "
                             "$MAKEFUN_OUTPUT_DIR or /output)")
    parser.add_argument("--self-test", action="store_true",
                        help="validate ENTRY and check a byte-identical "
                             "write/read round-trip, then exit")
    parser.add_argument("--check", action="store_true",
                        help="validate ENTRY only (no file written) and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

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
    if _read_bytes(path) != ENTRY.encode("utf-8"):
        print(f"read-back mismatch in {path}", file=sys.stderr)
        return 1
    print(f"wrote {path} ({len(ENTRY)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
