# closure_drift over the 100 most-downloaded PyPI projects

Selection rule and method were fixed in [`PREREGISTRATION.md`](PREREGISTRATION.md) before the list
was built; the list ([`selection.tsv`](selection.tsv), ranking of 2026-10-01) was committed before the
first measurement. Measured 2026-10-04 with the 0.8.0 detector (sha256 `1125e51615efc3698f09e7bce92bc8647eb468db5471ca79b8ee202cef684cda`),
at its defaults, no flag and no per-repository tuning. Every repository is in the table; none was
dropped. The reports as emitted are in [`results/`](results/).

## What came out

| outcome | repositories |
|---|---|
| `clean` | 42 |
| `refused` | 34 |
| `drift` | 21 |
| `inconclusive` | 2 |
| `no_labels` | 1 |

**Drift: 21 of the 63 repositories where a determination was reached (`clean` + `drift`), and 21 of
all 100.**

The 34 refusals have one cause: at its defaults the detector found no version label. Those are
largely projects whose version is derived from the tag itself at build time; nothing is claimed
about them.

The 42 `clean` verdicts cover 2943 of the 4632 tags scanned in those repositories; the rest declared
no version at that tag and were not compared.

## Reading the 21, honestly

This part is **not pre-registered**: it is a reading of the rows after the fact, and is marked as
such.

In 7 of the 21, the default version source found **three labels or fewer** across dozens of tags
(`pytest-dev/pytest`, `fsspec/filesystem_spec`, `pandas-dev/pandas`, `open-telemetry/opentelemetry-python`, `tqdm/tqdm`, `grpc/grpc`, `pydantic/jiter`). That is a constant
string in a file while the released version comes from somewhere else — the tag, a build step.
It is drift by this tool's definition under its defaults, and it says the defaults read the wrong
file for those projects, not that their releases are ambiguous. Pointing `--version-file` at the
real source would be a different measurement, and was excluded by the rule: no tuning.

In the other 14, the label moves with the releases — tens to hundreds of distinct labels — and
between one and six of them name more than one closure. Those are the case this tool is about:
two tags, one declared version, different code.

The limits stated before the run stand: the default closure globs are a guess about what determines
each project's output, and the 400 most recent tags are scanned. No maintainer was contacted and no
project is described as badly run; drift is a property of an addressing scheme.

## Every row

| rank | project | repository | outcome | scanned | compared | labels | in drift | worst |
|---|---|---|---|---|---|---|---|---|
| 1 | boto3 | `boto/boto3` | clean | 400 | 400 | 400 | 0 | 1 |
| 2 | packaging | `pypa/packaging` | clean | 53 | 14 | 14 | 0 | 1 |
| 3 | typing-extensions | `python/typing_extensions` | clean | 58 | 41 | 41 | 0 | 1 |
| 4 | idna | `kjd/idna` | refused: no label found |  |  |  |  |  |
| 5 | urllib3 | `urllib3/urllib3` | refused: no label found |  |  |  |  |  |
| 6 | certifi | `certifi/python-certifi` | refused: no label found |  |  |  |  |  |
| 7 | requests | `psf/requests` | clean | 162 | 12 | 12 | 0 | 1 |
| 8 | charset-normalizer | `jawah/charset_normalizer` | clean | 64 | 12 | 12 | 0 | 1 |
| 9 | cryptography | `pyca/cryptography` | clean | 161 | 48 | 48 | 0 | 1 |
| 10 | setuptools | `pypa/setuptools` | clean | 400 | 72 | 70 | 0 | 1 |
| 11 | cffi | `python-cffi/cffi` | clean | 33 | 4 | 4 | 0 | 1 |
| 12 | pygments | `pygments/pygments` | drift | 70 | 70 | 69 | 1 | 2 |
| 13 | pyyaml | `yaml/pyyaml` | refused: no label found |  |  |  |  |  |
| 14 | python-dateutil | `dateutil/dateutil` | refused: no label found |  |  |  |  |  |
| 15 | six | `benjaminp/six` | refused: no label found |  |  |  |  |  |
| 17 | botocore | `boto/botocore` | clean | 400 | 400 | 400 | 0 | 1 |
| 18 | pydantic | `pydantic/pydantic` | refused: no label found |  |  |  |  |  |
| 19 | pycparser | `eliben/pycparser` | inconclusive | 25 | 1 | 1 | 0 | 1 |
| 20 | click | `pallets/click` | clean | 71 | 11 | 11 | 0 | 1 |
| 22 | anyio | `agronholm/anyio` | refused: no label found |  |  |  |  |  |
| 23 | numpy | `numpy/numpy` | clean | 280 | 53 | 53 | 0 | 1 |
| 24 | pytest | `pytest-dev/pytest` | drift | 224 | 137 | 1 | 1 | 122 |
| 25 | iniconfig | `pytest-dev/iniconfig` | refused: no label found |  |  |  |  |  |
| 26 | annotated-types | `annotated-types/annotated-types` | clean | 8 | 8 | 8 | 0 | 1 |
| 27 | h11 | `python-hyper/h11` | refused: no label found |  |  |  |  |  |
| 28 | typing-inspection | `pydantic/typing-inspection` | clean | 9 | 9 | 9 | 0 | 1 |
| 29 | attrs | `python-attrs/attrs` | refused: no label found |  |  |  |  |  |
| 30 | s3transfer | `boto/s3transfer` | clean | 63 | 63 | 63 | 0 | 1 |
| 31 | aiobotocore | `aio-libs/aiobotocore` | drift | 142 | 142 | 140 | 1 | 3 |
| 33 | httpx | `encode/httpx` | clean | 88 | 69 | 69 | 0 | 1 |
| 34 | markupsafe | `pallets/markupsafe` | clean | 39 | 5 | 5 | 0 | 1 |
| 35 | httpcore | `encode/httpcore` | drift | 55 | 55 | 54 | 1 | 2 |
| 36 | python-dotenv | `theskumar/python-dotenv` | clean | 53 | 28 | 28 | 0 | 1 |
| 37 | pyjwt | `jpadilla/pyjwt` | clean | 52 | 48 | 48 | 0 | 1 |
| 38 | platformdirs | `tox-dev/platformdirs` | refused: no label found |  |  |  |  |  |
| 39 | fsspec | `fsspec/filesystem_spec` | drift | 103 | 2 | 1 | 1 | 2 |
| 40 | pandas | `pandas-dev/pandas` | drift | 194 | 117 | 3 | 3 | 52 |
| 41 | jinja2 | `pallets/jinja` | no_labels | 55 | 0 | 0 | 0 | 0 |
| 42 | jmespath | `jmespath/jmespath.py` | clean | 27 | 27 | 27 | 0 | 1 |
| 43 | pathspec | `cpburnz/python-pathspec` | clean | 18 | 7 | 7 | 0 | 1 |
| 44 | filelock | `tox-dev/py-filelock` | refused: no label found |  |  |  |  |  |
| 45 | starlette | `Kludex/starlette` | drift | 199 | 199 | 197 | 1 | 2 |
| 46 | uvicorn | `Kludex/uvicorn` | clean | 204 | 204 | 203 | 0 | 1 |
| 47 | multidict | `aio-libs/multidict` | clean | 175 | 175 | 173 | 0 | 1 |
| 48 | jsonschema | `python-jsonschema/jsonschema` | refused: no label found |  |  |  |  |  |
| 49 | rpds-py | `crate-py/rpds` | drift | 88 | 88 | 79 | 4 | 3 |
| 50 | yarl | `aio-libs/yarl` | drift | 155 | 155 | 153 | 1 | 2 |
| 51 | aiohttp | `aio-libs/aiohttp` | drift | 330 | 318 | 311 | 5 | 2 |
| 52 | rich | `Textualize/rich` | drift | 178 | 178 | 168 | 6 | 2 |
| 53 | tomlkit | `python-poetry/tomlkit` | clean | 55 | 55 | 55 | 0 | 1 |
| 54 | markdown-it-py | `executablebooks/markdown-it-py` | drift | 49 | 49 | 44 | 1 | 3 |
| 55 | propcache | `aio-libs/propcache` | clean | 14 | 12 | 12 | 0 | 1 |
| 56 | referencing | `python-jsonschema/referencing` | refused: no label found |  |  |  |  |  |
| 57 | jsonschema-specifications | `python-jsonschema/jsonschema-specifications` | refused: no label found |  |  |  |  |  |
| 58 | mdurl | `executablebooks/mdurl` | clean | 4 | 4 | 4 | 0 | 1 |
| 59 | pillow | `python-pillow/Pillow` | clean | 99 | 47 | 47 | 0 | 1 |
| 60 | opentelemetry-api | `open-telemetry/opentelemetry-python` | drift | 88 | 23 | 1 | 1 | 23 |
| 61 | frozenlist | `aio-libs/frozenlist` | clean | 27 | 27 | 27 | 0 | 1 |
| 62 | tqdm | `tqdm/tqdm` | drift | 175 | 48 | 1 | 1 | 45 |
| 63 | pip | `pypa/pip` | clean | 165 | 95 | 95 | 0 | 1 |
| 64 | googleapis-common-protos | `googleapis/google-cloud-python` | refused: no label found |  |  |  |  |  |
| 65 | pyasn1 | `pyasn1/pyasn1` | clean | 25 | 25 | 25 | 0 | 1 |
| 66 | aiosignal | `aio-libs/aiosignal` | clean | 14 | 14 | 14 | 0 | 1 |
| 67 | aiohappyeyeballs | `aio-libs/aiohappyeyeballs` | clean | 47 | 47 | 47 | 0 | 1 |
| 68 | websockets | `python-websockets/websockets` | refused: no label found |  |  |  |  |  |
| 69 | annotated-doc | `fastapi/annotated-doc` | clean | 4 | 2 | 2 | 0 | 1 |
| 70 | wrapt | `GrahamDumpleton/wrapt` | refused: no label found |  |  |  |  |  |
| 71 | pytz | `stub42/pytz` | refused: no label found |  |  |  |  |  |
| 72 | sniffio | `python-trio/sniffio` | clean | 5 | 5 | 5 | 0 | 1 |
| 73 | tzdata | `python/tzdata` | clean | 53 | 53 | 46 | 0 | 1 |
| 74 | fastapi | `fastapi/fastapi` | clean | 308 | 308 | 308 | 0 | 1 |
| 76 | zipp | `jaraco/zipp` | refused: no label found |  |  |  |  |  |
| 77 | greenlet | `python-greenlet/greenlet` | clean | 68 | 45 | 45 | 0 | 1 |
| 78 | importlib-metadata | `python/importlib_metadata` | refused: no label found |  |  |  |  |  |
| 79 | pydantic-settings | `pydantic/pydantic-settings` | refused: no label found |  |  |  |  |  |
| 80 | wheel | `pypa/wheel` | clean | 72 | 30 | 30 | 0 | 1 |
| 81 | tenacity | `jd/tenacity` | refused: no label found |  |  |  |  |  |
| 82 | trove-classifiers | `pypa/trove-classifiers` | refused: no label found |  |  |  |  |  |
| 83 | python-multipart | `Kludex/python-multipart` | clean | 30 | 20 | 20 | 0 | 1 |
| 84 | pyasn1-modules | `pyasn1/pyasn1-modules` | drift | 20 | 20 | 19 | 1 | 2 |
| 86 | pyarrow | `apache/arrow` | refused: no label found |  |  |  |  |  |
| 87 | sqlalchemy | `sqlalchemy/sqlalchemy` | drift | 343 | 314 | 290 | 1 | 25 |
| 88 | hatchling | `pypa/hatch` | refused: no label found |  |  |  |  |  |
| 89 | grpcio | `grpc/grpc` | drift | 400 | 289 | 1 | 1 | 288 |
| 90 | pyparsing | `pyparsing/pyparsing` | refused: no label found |  |  |  |  |  |
| 91 | lxml | `lxml/lxml` | refused: no label found |  |  |  |  |  |
| 92 | jiter | `pydantic/jiter` | drift | 34 | 4 | 1 | 1 | 4 |
| 93 | regex | `mrabarnett/mrab-regex` | drift | 88 | 50 | 38 | 5 | 2 |
| 94 | watchfiles | `samuelcolvin/watchfiles` | drift | 44 | 30 | 11 | 2 | 11 |
| 95 | s3fs | `fsspec/s3fs` | refused: no label found |  |  |  |  |  |
| 96 | ruff | `astral-sh/ruff` | drift | 400 | 247 | 246 | 1 | 2 |
| 97 | scipy | `scipy/scipy` | clean | 188 | 30 | 30 | 0 | 1 |
| 98 | soupsieve | `facelessuser/soupsieve` | refused: no label found |  |  |  |  |  |
| 100 | openai | `openai/openai-python` | clean | 400 | 372 | 372 | 0 | 1 |
| 103 | psutil | `giampaolo/psutil` | clean | 204 | 10 | 5 | 0 | 1 |
| 104 | coverage | `coveragepy/coveragepy` | refused: no label found |  |  |  |  |  |
| 107 | tomli | `hukkin/tomli` | clean | 32 | 32 | 32 | 0 | 1 |
| 108 | distro | `python-distro/distro` | refused: no label found |  |  |  |  |  |
| 110 | shellingham | `sarugaku/shellingham` | refused: no label found |  |  |  |  |  |
| 111 | mypy-extensions | `python/mypy_extensions` | inconclusive | 7 | 1 | 1 | 0 | 1 |

## Reproduce

```bash
python3 tools/study/run_study.py /some/empty/dir   # clones, measures and deletes one repository at a time
```
