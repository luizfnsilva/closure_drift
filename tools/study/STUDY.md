# Do Python projects' version labels always identify one code state?

The 100 most-downloaded PyPI projects with a public repository, measured with `closure_drift`
at its defaults. The selection rule and the method were written down before the first run
([`PREREGISTRATION.md`](PREREGISTRATION.md)); the list ([`selection.tsv`](selection.tsv)) was
committed before any measurement. No repository was tuned, added or dropped.

**Reproduce it, look at the cases, and say where the method is wrong.**

## Result

| outcome | run 1 | run 2 |
|---|---|---|
| `clean` | 42 | 63 |
| `drift` | 21 | 29 |
| no label found | 34 | 7 |
| `inconclusive` | 2 | 1 |
| `no_labels` | 1 | 0 |
| **total** | 100 | 100 |

**Run 2: a version label names more than one code state in 29 of the 92 repositories where a
determination was reached, and in 29 of all 100.** The 8 undecided stay in the denominator
of the second figure; they are listed below.

- 8767 of 10175 tags scanned in the decided repositories were compared; the rest declare no version.
- 87 version labels are in drift in all; every one is a line in [`collisions.tsv`](collisions.tsv).
- In 10 of the 63 `clean` repositories the version is derived from the tag itself. There
  `clean` holds by construction: it says only that no two tags give the same version.
- In 4 of the 29 in drift the colliding tags belong to different families (a monorepo
  releasing several packages from one version file): `grpc/grpc`, `pydantic/jiter`, `pydantic/pydantic`, `pypa/hatch`.

## Why there are two runs

Run 1 said more about the tool than about the projects: it read the version from one file
chosen at HEAD, so 34 repositories gave no label and several others were read from a constant
that is not the released version. The detector was changed for that — the source is resolved at
each tag, declared pointers are followed, and a version derived from the tag is read from the
tag — with the change written down before run 2 (`PREREGISTRATION.md`, run 2). Run 1 is kept,
every row, in [`run1/`](run1/). 46 repositories changed outcome between the runs:

| repository | run 1 | run 2 |
|---|---|---|
| `agronholm/anyio` | no label found | clean |
| `annotated-types/annotated-types` | clean | drift |
| `benjaminp/six` | no label found | clean |
| `certifi/python-certifi` | no label found | clean |
| `coveragepy/coveragepy` | no label found | clean |
| `dateutil/dateutil` | no label found | clean |
| `eliben/pycparser` | inconclusive | clean |
| `fsspec/filesystem_spec` | drift | clean |
| `fsspec/s3fs` | no label found | clean |
| `giampaolo/psutil` | clean | drift |
| `jaraco/zipp` | no label found | clean |
| `jd/tenacity` | no label found | clean |
| `kjd/idna` | no label found | clean |
| `lxml/lxml` | no label found | drift |
| `numpy/numpy` | clean | drift |
| `open-telemetry/opentelemetry-python` | drift | no label found |
| `openai/openai-python` | clean | drift |
| `pallets/click` | clean | drift |
| `pallets/jinja` | no_labels | drift |
| `pallets/markupsafe` | clean | drift |
| `pandas-dev/pandas` | drift | clean |
| `psf/requests` | clean | drift |
| `pydantic/pydantic` | no label found | drift |
| `pydantic/pydantic-settings` | no label found | clean |
| `pypa/hatch` | no label found | drift |
| `pyparsing/pyparsing` | no label found | inconclusive |
| `pytest-dev/iniconfig` | no label found | clean |
| `pytest-dev/pytest` | drift | clean |
| `python-attrs/attrs` | no label found | clean |
| `python-cffi/cffi` | clean | drift |
| `python-distro/distro` | no label found | clean |
| `python-greenlet/greenlet` | clean | drift |
| `python-hyper/h11` | no label found | clean |
| `python-jsonschema/jsonschema` | no label found | clean |
| `python-jsonschema/jsonschema-specifications` | no label found | clean |
| `python-jsonschema/referencing` | no label found | clean |
| `python-websockets/websockets` | no label found | clean |
| `python/importlib_metadata` | no label found | clean |
| `python/mypy_extensions` | inconclusive | clean |
| `sarugaku/shellingham` | no label found | clean |
| `sqlalchemy/sqlalchemy` | drift | clean |
| `tox-dev/platformdirs` | no label found | clean |
| `tox-dev/py-filelock` | no label found | clean |
| `tqdm/tqdm` | drift | clean |
| `urllib3/urllib3` | no label found | clean |
| `yaml/pyyaml` | no label found | drift |

## Limits

- Defaults only. The default closure globs are a guess about what determines each project's
  output; a collision here means two tags declare one version and differ in files those globs
  match.
- A collision is not a judgement. Common causes seen in the table: a tag created without
  bumping the version, maintenance-branch markers such as `7.x`, and tag families.
- The 400 most recent tags are scanned. Labels are compared as written.
- One person measured, on one machine. Nobody outside has reproduced it yet.
- No maintainer was contacted before publication.

## Reproduce

```bash
python3 tools/study/run_study.py /some/empty/dir     # clones, measures, deletes — about 40 minutes
python3 tools/study/make_report.py                    # rebuilds this page and collisions.tsv
```

One collision, by hand — any line of `collisions.tsv`:

```bash
git clone https://github.com/psf/requests && cd requests
closure-drift --compare v2.16.0 v2.16.1     # both declare 2.16.0; the paths that differ are listed
```

Detector: run 2 sha256 `6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`, run 1 `6df9787eb57df52b42e05c1eaab6c9ea21583ddcd3a78e73c2908760ac463aab`.
The reports as emitted are in [`results/`](results/) and [`run1/results/`](run1/results/).

## Every repository

| rank | project | repository | run 1 | run 2 | tags compared | labels | in drift | label read from |
|---|---|---|---|---|---|---|---|---|
| 1 | boto3 | `boto/boto3` | clean | clean | 400 of 400 | 400 | 0 | `boto3/__init__.py` |
| 2 | packaging | `pypa/packaging` | clean | clean | 50 of 53 | 50 | 0 | `packaging/__about__.py`, `src/packaging/__init__.py` |
| 3 | typing-extensions | `python/typing_extensions` | clean | clean | 58 of 58 | 57 | 0 | `pyproject.toml`, `setup.py` |
| 4 | idna | `kjd/idna` | no label found | clean | 17 of 43 | 17 | 0 | `idna/package_data.py` |
| 5 | urllib3 | `urllib3/urllib3` | no label found | clean | 109 of 109 | 108 | 0 | `(the tag)`, `setup.py`, `src/urllib3/__init__.py` |
| 6 | certifi | `certifi/python-certifi` | no label found | clean | 66 of 66 | 66 | 0 | `certifi/__init__.py`, `setup.py` |
| 7 | requests | `psf/requests` | clean | drift | 145 of 162 | 140 | 3 | `requests/__init__.py`, `requests/__version__.py`, `setup.py` |
| 8 | charset-normalizer | `jawah/charset_normalizer` | clean | clean | 55 of 64 | 55 | 0 | `charset_normalizer/version.py`, `setup.py`, `src/charset_normalizer/version.py` |
| 9 | cryptography | `pyca/cryptography` | clean | clean | 91 of 161 | 91 | 0 | `cryptography/__about__.py`, `pyproject.toml`, `src/cryptography/__about__.py` |
| 10 | setuptools | `pypa/setuptools` | clean | clean | 302 of 400 | 302 | 0 | `(the tag)`, `setup.cfg` |
| 11 | cffi | `python-cffi/cffi` | clean | drift | 33 of 33 | 32 | 1 | `pyproject.toml`, `setup.py` |
| 12 | pygments | `pygments/pygments` | drift | drift | 70 of 70 | 69 | 1 | `pygments/__init__.py`, `setup.py` |
| 13 | pyyaml | `yaml/pyyaml` | no label found | drift | 46 of 46 | 41 | 3 | `lib/yaml/__init__.py`, `setup.py` |
| 14 | python-dateutil | `dateutil/dateutil` | no label found | clean | 21 of 22 | 21 | 0 | `(the tag)`, `dateutil/__init__.py` |
| 15 | six | `benjaminp/six` | no label found | clean | 26 of 26 | 26 | 0 | `six.py` |
| 17 | botocore | `boto/botocore` | clean | clean | 400 of 400 | 400 | 0 | `botocore/__init__.py` |
| 18 | pydantic | `pydantic/pydantic` | no label found | drift | 151 of 218 | 138 | 1 | `pydantic/version.py` |
| 19 | pycparser | `eliben/pycparser` | inconclusive | clean | 25 of 25 | 25 | 0 | `pyproject.toml`, `setup.py` |
| 20 | click | `pallets/click` | clean | drift | 71 of 71 | 66 | 3 | `click/__init__.py`, `pyproject.toml`, `setup.py` |
| 22 | anyio | `agronholm/anyio` | no label found | clean | 72 of 72 | 72 | 0 | `(the tag)` |
| 23 | numpy | `numpy/numpy` | clean | drift | 126 of 280 | 125 | 1 | `(the tag)`, `numpy/version.py`, `pyproject.toml` |
| 24 | pytest | `pytest-dev/pytest` | drift | clean | 215 of 224 | 214 | 0 | `(the tag)`, `_pytest/__init__.py`, `setup.py` |
| 25 | iniconfig | `pytest-dev/iniconfig` | no label found | clean | 8 of 9 | 8 | 0 | `(the tag)` |
| 26 | annotated-types | `annotated-types/annotated-types` | clean | drift | 8 of 8 | 6 | 1 | `annotated_types/__init__.py`, `pyproject.toml` |
| 27 | h11 | `python-hyper/h11` | no label found | clean | 13 of 13 | 13 | 0 | `h11/_version.py` |
| 28 | typing-inspection | `pydantic/typing-inspection` | clean | clean | 9 of 9 | 9 | 0 | `pyproject.toml` |
| 29 | attrs | `python-attrs/attrs` | no label found | clean | 33 of 38 | 32 | 0 | `(the tag)`, `attr/__init__.py`, `src/attr/__init__.py` |
| 30 | s3transfer | `boto/s3transfer` | clean | clean | 63 of 63 | 63 | 0 | `s3transfer/__init__.py` |
| 31 | aiobotocore | `aio-libs/aiobotocore` | drift | drift | 142 of 142 | 140 | 1 | `aiobotocore/__init__.py` |
| 33 | httpx | `encode/httpx` | clean | clean | 88 of 88 | 88 | 0 | `http3/__init__.py`, `http3/__version__.py`, `httpcore/__init__.py` |
| 34 | markupsafe | `pallets/markupsafe` | clean | drift | 39 of 39 | 35 | 2 | `markupsafe/__init__.py`, `pyproject.toml`, `setup.py` |
| 35 | httpcore | `encode/httpcore` | drift | drift | 55 of 55 | 54 | 1 | `httpcore/__init__.py` |
| 36 | python-dotenv | `theskumar/python-dotenv` | clean | clean | 53 of 53 | 53 | 0 | `dotenv/version.py`, `setup.py`, `src/dotenv/version.py` |
| 37 | pyjwt | `jpadilla/pyjwt` | clean | clean | 52 of 52 | 52 | 0 | `jwt/__init__.py`, `setup.py` |
| 38 | platformdirs | `tox-dev/platformdirs` | no label found | clean | 82 of 95 | 82 | 0 | `(the tag)` |
| 39 | fsspec | `fsspec/filesystem_spec` | drift | clean | 103 of 103 | 103 | 0 | `(the tag)` |
| 40 | pandas | `pandas-dev/pandas` | drift | clean | 134 of 194 | 133 | 0 | `(the tag)`, `pandas/version.py` |
| 41 | jinja2 | `pallets/jinja` | no_labels | drift | 54 of 55 | 51 | 2 | `jinja2/__init__.py`, `setup.py`, `src/jinja2/__init__.py` |
| 42 | jmespath | `jmespath/jmespath.py` | clean | clean | 27 of 27 | 27 | 0 | `setup.py` |
| 43 | pathspec | `cpburnz/python-pathspec` | clean | clean | 17 of 18 | 17 | 0 | `pathspec/__init__.py`, `pathspec/_meta.py`, `pathspec/_version.py` |
| 44 | filelock | `tox-dev/py-filelock` | no label found | clean | 106 of 135 | 106 | 0 | `(the tag)` |
| 45 | starlette | `Kludex/starlette` | drift | drift | 199 of 199 | 197 | 1 | `starlette/__init__.py` |
| 46 | uvicorn | `Kludex/uvicorn` | clean | clean | 204 of 204 | 203 | 0 | `uvicorn/__init__.py` |
| 47 | multidict | `aio-libs/multidict` | clean | clean | 175 of 175 | 173 | 0 | `multidict/__init__.py` |
| 48 | jsonschema | `python-jsonschema/jsonschema` | no label found | clean | 95 of 111 | 95 | 0 | `(the tag)`, `jsonschema/__init__.py` |
| 49 | rpds-py | `crate-py/rpds` | drift | drift | 88 of 88 | 79 | 4 | `Cargo.toml` |
| 50 | yarl | `aio-libs/yarl` | drift | drift | 155 of 155 | 153 | 1 | `yarl/__init__.py` |
| 51 | aiohttp | `aio-libs/aiohttp` | drift | drift | 330 of 330 | 323 | 4 | `aiohttp/__init__.py`, `setup.py` |
| 52 | rich | `Textualize/rich` | drift | drift | 178 of 178 | 168 | 6 | `pyproject.toml` |
| 53 | tomlkit | `python-poetry/tomlkit` | clean | clean | 55 of 55 | 55 | 0 | `pyproject.toml` |
| 54 | markdown-it-py | `executablebooks/markdown-it-py` | drift | drift | 49 of 49 | 44 | 1 | `markdown_it/__init__.py` |
| 55 | propcache | `aio-libs/propcache` | clean | clean | 13 of 14 | 13 | 0 | `propcache/__init__.py`, `src/propcache/__init__.py` |
| 56 | referencing | `python-jsonschema/referencing` | no label found | clean | 124 of 124 | 124 | 0 | `(the tag)` |
| 57 | jsonschema-specifications | `python-jsonschema/jsonschema-specifications` | no label found | clean | 27 of 27 | 27 | 0 | `(the tag)` |
| 58 | mdurl | `executablebooks/mdurl` | clean | clean | 4 of 4 | 4 | 0 | `src/mdurl/__init__.py` |
| 59 | pillow | `python-pillow/Pillow` | clean | clean | 77 of 99 | 77 | 0 | `PIL/version.py`, `setup.py`, `src/PIL/_version.py` |
| 60 | opentelemetry-api | `open-telemetry/opentelemetry-python` | drift | no label found |  |  |  |  |
| 61 | frozenlist | `aio-libs/frozenlist` | clean | clean | 27 of 27 | 27 | 0 | `frozenlist/__init__.py` |
| 62 | tqdm | `tqdm/tqdm` | drift | clean | 49 of 175 | 49 | 0 | `(the tag)`, `setup.py` |
| 63 | pip | `pypa/pip` | clean | clean | 165 of 165 | 165 | 0 | `pip/__init__.py`, `setup.py`, `src/pip/__init__.py` |
| 64 | googleapis-common-protos | `googleapis/google-cloud-python` | no label found | no label found |  |  |  |  |
| 65 | pyasn1 | `pyasn1/pyasn1` | clean | clean | 25 of 25 | 25 | 0 | `pyasn1/__init__.py` |
| 66 | aiosignal | `aio-libs/aiosignal` | clean | clean | 14 of 14 | 14 | 0 | `aiosignal/__init__.py` |
| 67 | aiohappyeyeballs | `aio-libs/aiohappyeyeballs` | clean | clean | 47 of 47 | 47 | 0 | `pyproject.toml` |
| 68 | websockets | `python-websockets/websockets` | no label found | clean | 29 of 53 | 29 | 0 | `src/websockets/version.py`, `websockets/version.py` |
| 69 | annotated-doc | `fastapi/annotated-doc` | clean | clean | 4 of 4 | 4 | 0 | `pyproject.toml`, `src/annotated_doc/__init__.py` |
| 70 | wrapt | `GrahamDumpleton/wrapt` | no label found | no label found |  |  |  |  |
| 71 | pytz | `stub42/pytz` | no label found | no label found |  |  |  |  |
| 72 | sniffio | `python-trio/sniffio` | clean | clean | 5 of 5 | 5 | 0 | `sniffio/_version.py` |
| 73 | tzdata | `python/tzdata` | clean | clean | 53 of 53 | 46 | 0 | `VERSION` |
| 74 | fastapi | `fastapi/fastapi` | clean | clean | 308 of 308 | 308 | 0 | `fastapi/__init__.py` |
| 76 | zipp | `jaraco/zipp` | no label found | clean | 68 of 69 | 67 | 0 | `(the tag)` |
| 77 | greenlet | `python-greenlet/greenlet` | clean | drift | 68 of 68 | 67 | 1 | `setup.py`, `src/greenlet/__init__.py` |
| 78 | importlib-metadata | `python/importlib_metadata` | no label found | clean | 122 of 131 | 122 | 0 | `(the tag)` |
| 79 | pydantic-settings | `pydantic/pydantic-settings` | no label found | clean | 39 of 39 | 39 | 0 | `pydantic_settings/version.py` |
| 80 | wheel | `pypa/wheel` | clean | clean | 72 of 72 | 72 | 0 | `(the tag)`, `setup.py`, `src/wheel/__init__.py` |
| 81 | tenacity | `jd/tenacity` | no label found | clean | 65 of 75 | 65 | 0 | `(the tag)` |
| 82 | trove-classifiers | `pypa/trove-classifiers` | no label found | no label found |  |  |  |  |
| 83 | python-multipart | `Kludex/python-multipart` | clean | clean | 30 of 30 | 30 | 0 | `multipart/__init__.py`, `multipart/_version.py`, `python_multipart/__init__.py` |
| 84 | pyasn1-modules | `pyasn1/pyasn1-modules` | drift | drift | 20 of 20 | 19 | 1 | `pyasn1_modules/__init__.py` |
| 86 | pyarrow | `apache/arrow` | no label found | no label found |  |  |  |  |
| 87 | sqlalchemy | `sqlalchemy/sqlalchemy` | drift | clean | 318 of 343 | 318 | 0 | `lib/sqlalchemy/__init__.py`, `setup.py` |
| 88 | hatchling | `pypa/hatch` | no label found | drift | 154 of 154 | 94 | 26 | `(the tag)`, `hatch/__about__.py`, `hatch/__init__.py` |
| 89 | grpcio | `grpc/grpc` | drift | drift | 380 of 400 | 370 | 5 | `src/python/grpcio/grpc_version.py` |
| 90 | pyparsing | `pyparsing/pyparsing` | no label found | inconclusive | 1 of 79 | 1 | 0 | `pyparsing/__init__.py` |
| 91 | lxml | `lxml/lxml` | no label found | drift | 60 of 165 | 45 | 3 | `setup.py`, `src/lxml/__init__.py` |
| 92 | jiter | `pydantic/jiter` | drift | drift | 34 of 34 | 29 | 2 | `Cargo.toml`, `pyproject.toml` |
| 93 | regex | `mrabarnett/mrab-regex` | drift | drift | 88 of 88 | 66 | 6 | `pyproject.toml`, `setup.py` |
| 94 | watchfiles | `samuelcolvin/watchfiles` | drift | drift | 21 of 44 | 12 | 1 | `Cargo.toml`, `watchfiles/version.py`, `watchgod/version.py` |
| 95 | s3fs | `fsspec/s3fs` | no label found | clean | 91 of 91 | 91 | 0 | `(the tag)`, `setup.py` |
| 96 | ruff | `astral-sh/ruff` | drift | drift | 247 of 400 | 246 | 1 | `pyproject.toml` |
| 97 | scipy | `scipy/scipy` | clean | clean | 43 of 188 | 43 | 0 | `Lib/version.py`, `pyproject.toml`, `scipy/version.py` |
| 98 | soupsieve | `facelessuser/soupsieve` | no label found | no label found |  |  |  |  |
| 100 | openai | `openai/openai-python` | clean | drift | 400 of 400 | 397 | 3 | `openai/version.py`, `pyproject.toml` |
| 103 | psutil | `giampaolo/psutil` | clean | drift | 198 of 204 | 98 | 1 | `psutil/__init__.py` |
| 104 | coverage | `coveragepy/coveragepy` | no label found | clean | 36 of 192 | 36 | 0 | `coverage/__init__.py`, `coverage/version.py` |
| 107 | tomli | `hukkin/tomli` | clean | clean | 32 of 32 | 32 | 0 | `pyproject.toml`, `src/tomli/__init__.py`, `tomli/__init__.py` |
| 108 | distro | `python-distro/distro` | no label found | clean | 21 of 21 | 20 | 0 | `distro.py`, `setup.py`, `src/distro/distro.py` |
| 110 | shellingham | `sarugaku/shellingham` | no label found | clean | 19 of 21 | 19 | 0 | `src/shellingham/__init__.py` |
| 111 | mypy-extensions | `python/mypy_extensions` | inconclusive | clean | 7 of 7 | 7 | 0 | `pyproject.toml`, `setup.py` |
