# Where the version label is read from

At each tag, in this order. The first rule that yields a plausible version wins; `--version-file`
turns all of it off and reads that one file.

**A Python project** (it has `pyproject.toml`, `setup.cfg` or `setup.py`):

1. **A pointer the build declares** — `[tool.hatch.version] path`, `version = {attr = "pkg.__version__"}`
   or `{file = "..."}` under `[tool.setuptools.dynamic]`, `attr:` / `file:` in `setup.cfg`, the
   module of a flit project, `Cargo.toml` for maturin.
2. **A tool the build declares that derives the version from the tag** — `setuptools_scm`,
   `hatch-vcs`, `versioneer`, `versioningit`, `poetry-dynamic-versioning`, `pbr`. The label is then
   the tag name, without a `word-` prefix or a leading `v`.
3. **A version written in the build files** — `[project]` or `[tool.poetry]` in `pyproject.toml`,
   `[metadata]` in `setup.cfg`, the `version=` argument of `setup(...)`.
4. **The version module of the project's own package** — `__version__.py`, `_version.py`,
   `version.py`, `__about__.py`, `__init__.py` in the package the project names, the packages
   `setup.py` lists, or the only top-level package there is.

**Otherwise**: `Cargo.toml`, `package.json`, `composer.json`, `build.gradle`, `VERSION`, `version.txt`.

## What counts as a label

A string with a digit in it, that is not a format template (`%(version)s`, `{}.{}`) and not a
placeholder (`0.0.0`). An assignment counts only at the start of a line and only when the string is
the whole right-hand side: `__version__ = "1.2"` yes, `__version__ = ".".join(...)` no.

## When the rules find nothing, or the wrong file

From 0.10.0 a file found by the rules is not believed when no tag named for a version has ever
agreed with it (`v1` agrees with `1.2.3`; `v2.52` does not agree with `0.1.0`). The report names it
under `contradicted_sources`. A file you pass with `--version-file` is never second-guessed.

A version spread over several lines: name the groups `part1`, `part2`, … Their values are joined
with `.`, and a value starting with `-` or `+` is attached as it is. Otherwise group 1 is the label.

Recipes for large projects, written before they were run (`tools/benchmark/recipes.json`; results
in `tools/benchmark/READING.md`, run 2):

| project | version file | pattern |
|---|---|---|
| Linux | `Makefile` | `(?m)^VERSION = (?P<part1>\d+)\nPATCHLEVEL = (?P<part2>\d+)\nSUBLEVEL = (?P<part3>\d+)\nEXTRAVERSION =[ \t]*(?P<part4>\S*)` |
| LLVM | `cmake/Modules/LLVMVersion.cmake` | `set\(LLVM_VERSION_MAJOR (?P<part1>\d+)\)[\s\S]*?set\(LLVM_VERSION_MINOR (?P<part2>\d+)\)[\s\S]*?set\(LLVM_VERSION_PATCH (?P<part3>\d+)\)` |
| Rust | `src/version` | (the file is the version) |
| CPython | `Include/patchlevel.h` | `#define PY_VERSION\s+"([^"]+)"` |
| Node.js | `src/node_version.h` | `#define NODE_MAJOR_VERSION (?P<part1>\d+)\s*\n#define NODE_MINOR_VERSION (?P<part2>\d+)\s*\n#define NODE_PATCH_VERSION (?P<part3>\d+)` |

LLVM kept its version in `llvm/CMakeLists.txt` before release 16; with one version file, older tags
have no label there. git and Kubernetes have no version file to read: the version comes from the tag (git's
`DEF_VER` is a fallback that is not bumped at each release, and a first recipe that read it found
39 labels in "drift" that are not), so the version is the tag, and a tag names one
commit, so there is nothing for this tool to measure.

## What it does not do

- It does not run `setup.py` or import anything. `setup.py` is parsed.
- It does not compute a version from a tuple (`version_info = (1, 2, 3)`), read generated files,
  or follow more than one import.
- It reads build files line by line; a build file over 1 MiB is not read.
- When the source changes between two tags and the earlier file still declares a different version
  at the later tag, the point is counted as `points_with_conflicting_sources` and the verdict is
  never `clean`.

The report says where every label came from: `label_sources` in JSON, a line in the text report.
