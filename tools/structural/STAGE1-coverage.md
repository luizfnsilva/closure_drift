# Etapa 1 do §35 — cobertura e mapa de chamadas (detector de 1.8.2)

`closure_drift.py` sha256 `c50974fcb4a5eb6cb51302dbc767a11a427343d9c88e397caab5d3156743edb4`. Baterias: fixture, battery (271/272), adversarial (303/315), properties (17/17), sob coverage.py, subprocessos incluídos. Mutantes não entram (mudam o arquivo).

Instruções: 1605 · executadas 1456 · **não executadas 149** (9,3%). Não executada é pergunta, não prova de sobra (§35).

## Funções (linhas, não executadas, quem chama)

"Chamada por" só conta chamadas diretas por nome; chamadas por tabela, atributo ou método aparecem como "—" e não significam função morta.

| função | linhas | não exec. | chamada por |
|---|---|---|---|
| `measure` | 319 | 6 | components, run |
| `run` | 130 | 3 | main |
| `check_tag` | 87 | 6 | measure |
| `compare` | 84 | 5 | measure |
| `would_tag` | 83 | 12 | measure |
| `components` | 64 | 5 | run |
| `read` | 58 | 10 | — |
| `python` | 58 | 2 | — |
| `at` | 51 | 0 | — |
| `setup_info` | 44 | 6 | read, setup |
| `read_config` | 42 | 3 | run |
| `publication_points` | 32 | 2 | measure |
| `main` | 30 | 5 | — |
| `children` | 27 | 1 | — |
| `tables` | 27 | 6 | check_tag, manifest_name, read, workspace_version |
| `diagnose_start` | 27 | 2 | run |
| `workspace_version` | 25 | 4 | — |
| `prefixed_source` | 24 | 1 | check_tag |
| `version_written_at_publish` | 22 | 2 | check_tag |
| `find` | 21 | 1 | — |
| `no_label_refusal` | 21 | 2 | measure |
| `read_published` | 20 | 1 | run |
| `print_coverage` | 19 | 1 | measure, would_tag |
| `packages` | 18 | 3 | — |
| `read` | 17 | 10 | — |
| `attribute` | 17 | 1 | — |
| `explain` | 17 | 1 | measure |
| `entries` | 16 | 1 | — |
| `bounded_search` | 16 | 2 | declared_version |
| `dirty_in_closure` | 16 | 5 | compare, measure |
| `ids` | 15 | 1 | — |
| `version_name_hint` | 15 | 2 | measure |
| `manifest_name` | 15 | 4 | prefixed_source |
| `diagnose_repository` | 15 | 0 | run |
| `check_globs` | 13 | 2 | components, run |
| `text` | 13 | 1 | — |
| `imported_from` | 13 | 2 | attribute |
| `drift_mechanisms` | 13 | 1 | measure |
| `working_tree_state` | 13 | 2 | check_tag, compare, components, measure |
| `print_method` | 13 | 0 | check_tag, compare, measure, would_tag |
| `git_bytes` | 12 | 1 | dirty_in_closure, git, local_config, modes, run, working_tree_state |
| `printable` | 12 | 1 | check_tag, compare, components, diagnose_start, git_bytes, measure, no_label_refusal, prefixed_source, print_coverage, print_next, print_sources, read, read_config, read_published, run, version_name_hint, working_tree_state, would_tag |
| `__init__` | 12 | 1 | — |
| `label_of` | 12 | 1 | bounded_search, match_on_stdin |
| `tag_versions` | 12 | 1 | check_tag, drift_mechanisms, publication_points |
| `__init__` | 12 | 1 | — |
| `local_config` | 11 | 2 | run, working_tree_state |
| `version_key` | 11 | 1 | __init__, at, check_tag, drift_mechanisms, label_twins, measure, publication_points, tag_versions |
| `label_twins` | 10 | 1 | measure |
| `modes` | 9 | 1 | — |
| `attribute_value` | 9 | 1 | read |
| `text` | 9 | 1 | — |
| `excluded_folders` | 8 | 1 | brought_in |
| `unique_keys` | 8 | 1 | — |
| `scm_derived` | 8 | 1 | check_tag |
| `print_sources` | 8 | 3 | measure |
| `excluded` | 7 | 1 | attribute, holds, prefixed_source |
| `git_version` | 7 | 1 | run |
| `close` | 7 | 1 | — |
| `declared_version` | 7 | 0 | at |
| `root_has_source` | 7 | 1 | measure |
| `badge` | 7 | 0 | check_tag, compare, components, measure, would_tag |
| `print_next` | 7 | 0 | check_tag, compare, measure, would_tag |
| `emit` | 6 | 0 | check_tag, compare, components, measure, would_tag |
| `holds` | 6 | 0 | — |
| `match_on_stdin` | 6 | 1 | main |
| `inherits_workspace_version` | 6 | 1 | read |
| `tree_cache_bound` | 5 | 0 | __init__ |
| `git_env` | 5 | 0 | __init__, diagnose_start, git_bytes, git_version |
| `matches` | 5 | 1 | brought_in, excluded, holds |
| `root_tree` | 5 | 1 | — |
| `closure_hash` | 5 | 1 | — |
| `plausible` | 5 | 1 | at, read |
| `__init__` | 5 | 1 | — |
| `tables` | 5 | 6 | check_tag, manifest_name, read, workspace_version |
| `setup` | 5 | 0 | — |
| `release_numbers` | 5 | 1 | at, compare |
| `tag_label` | 5 | 1 | at, check_tag |
| `contradicted` | 5 | 1 | — |
| `prerelease_key` | 5 | 1 | check_tag |
| `__init__` | 4 | 1 | — |
| `brought_in` | 4 | 1 | — |
| `member_map` | 4 | 1 | — |
| `source` | 4 | 0 | — |
| `tag_prefix` | 4 | 1 | prefixed_source |
| `git` | 3 | 0 | ask, check_tag, compare, diagnose_repository, no_label_refusal, publication_points, run, version_name_hint |
| `string` | 3 | 0 | manifest_name, python, read, scm_derived, workspace_version |
| `requirement` | 3 | 0 | python, scm_derived |
| `write` | 3 | 0 | — |
| `ask` | 3 | 0 | diagnose_repository |
| `named_folders` | 2 | 0 | brought_in, measure |
| `members` | 2 | 0 | — |
| `depth_first` | 2 | 0 | attribute, find |
| `__init__` | 2 | 1 | — |
| `flush` | 2 | 1 | — |
| `same_name` | 2 | 0 | prefixed_source |

## Linhas não executadas

Classificação (etapa 2): domínio · segurança · compatibilidade · possivelmente redundante.

### `would_tag`
```
 1746     """Before tagging: the label and closure of HEAD against the tags that exist. The answer is
 1800         print(f"NO LABEL AT HEAD: {printable(rejected['source'])} declares {printable(rejected['label'])}, and no tag")
 1801         print("named for a version has ever agreed with that file. It is not taken as your version.")
 1802         print("Pass --version-file with the file that declares it.")
 1811     elif verdict == "incomplete" and labels.sources.too_large:
 1812         print(f"INCOMPLETE: "
 1815         print("A version it may declare is unknown. Pass --version-file with the file that declares it.")
 1816     elif verdict == "no_label_at_head":
 1817         print(f"NO LABEL AT HEAD: {printable(vpath)} declares no version at this commit.")
 1819         print("EMPTY CLOSURE AT HEAD: the closure globs match no file at this commit.")
 1821         print(f"\n{len(drifting)} label(s) already in drift in the existing tags. That is history,")
 1822         print("and is not what this answer is about; run without --would-tag to see it.")
```
### `read`
```
  248         """The bytes of object `name`, which must be of type `want`."""
  260             raise Refusal(f"git cat-file failed while reading {printable(name[:60])}: {type(e).__name__}")
  262             raise Refusal(f"git cat-file returned a truncated {want} {printable(name[:60])}")
  633         """The label a source gives at this commit, or None when it gives no plausible one."""
  660                 value = None
  681             for line in text.split("\n"):
  682                 m = re.match(r'[ \t]*version[ \t]*=?[ \t]*["\']([^"\'\n]+)["\']', line)
  683                 if m:
  684                     value = m.group(1)
  685                     break
```
### `setup_info`
```
  503     """What `setup(...)` in a setup.py says about the version — parsed, never executed. A
  536                     info["scm"] = True
  539             elif kw.arg == "packages" and isinstance(v, (ast.List, ast.Tuple)):
  540                 info["packages"] = [e.value.split(".")[0] for e in v.elts
  542             elif kw.arg in ("use_scm_version", "pbr") and not (isinstance(v, ast.Constant) and not v.value):
  543                 info["scm"] = True
```
### `measure`
```
 1667         print(f"... and {len(by_label) - 25} more labels")
 1717         print(f"INCOMPLETE: no tag named for a version agrees with {', '.join(printable(p) for p in contradicted)},")
 1718         print("so it is probably not your version. Nothing is decided from it.")
 1719         print("Pass --version-file with the file that declares your version.")
 1729         print("INCOMPLETE: no label names more than one closure, but not every publication point")
 1730         print("scanned could be compared with confidence. See the counts below.")
```
### `check_tag`
```
 1937     """After tagging: the versions the tag's name can name against the label its commit declares. A tag
 1958             raise Refusal(f"--tag: the prefix of {printable(repr(name))} names {printable(by_prefix[0])}, which "
 1964         raise Refusal(NO_LABEL)
 1984         stamp["working_tree_dirty_note"] = dirty_note
 1986         print(badge(verdict, stamp["measured_at_head"]))
 1987         return code
```
### `tables`
```
  445     """{table: {key: right-hand side}} of a TOML or INI file. Read line by line, so the cost is
  452             out[table][last] += " " + line
  453             open_array = 0 if "]" in line or open_array > 200 else open_array + 1
  454             continue
  467                 open_array = 1
  469             out[table][last] += " " + line          # an INI continuation line
```
### `compare`
```
 2026     """Two references, side by side: the label and closure of each, and the paths of the closure
 2091             print(f"   {title:10s} ... and {len(paths) - 60} more")
 2094         print("IDENTICAL: the two references hold the same closure.")
 2102         print(f"NOT COMPARABLE: {printable(one['label_source'])} declares a version that neither tag agrees with;")
 2103         print("it is probably not your version. Pass --version-file with the file that declares it.")
```
### `dirty_in_closure`
```
 1166     """Whether a changed or untracked path of the working tree is in the closure (§20)."""
 1169         return None
 1176                 i += 1                                  # the source of a rename follows
 1177                 if i < len(fields) and fields[i]:
 1178                     paths.append(fields[i].decode("utf-8", "replace"))
```
### `main`
```
 2243     """The closed set of exit codes is enforced here: nothing leaves this function as a traceback,
 2263         try:
 2264             sys.stdout = open(os.devnull, "w")
 2266             pass
 2267         return 2
```
### `components`
```
 1358     """Every declared component, one report each, and one verdict: drift if any is in drift, clean if
 1398             stamp["working_tree_dirty_note"] = dirty_note
 1415     elif verdict == "clean":
 1416         print("CLEAN: every component is clean.")
 1418         print("INCOMPLETE: no component is in drift, but not every component could be decided.")
```
### `workspace_version`
```
  607         """[workspace.package].version of the root Cargo builds this member with: the file
  616                         return None
  626                 continue
  630         return None
```
### `manifest_name`
```
 1855     """The package name a manifest declares."""
 1861             return None
 1867     m = re.search(r'^name:[ \t]*["\']?([^"\'\s#]+)', text, re.M)
 1868     return m.group(1) if m else None
```
### `read_config`
```
 1107     """`.closure-drift.json`, checked. A broken file, a wrong type or an unknown key is a refusal."""
 1125             raise Refusal(f"broken {printable(cfg_path)}: every entry of {key!r} must be a non-empty string")
 1142                     raise Refusal(f"broken {printable(cfg_path)}: {where}: {key!r} must be a non-empty "
```
### `print_sources`
```
 2162         print(f"  at {labels.conflicts} point(s) the source changed and the earlier file still declares")
 2163         print("  a different version there: two files disagree, and that is never reported as clean.")
 2164         print("  Pass --version-file to say which one declares the version.")
```
### `run`
```
 1275         raise Refusal("this is a partial clone, and this git is older than 2.45: reading an object "
 1282         raise Refusal("--published lists the versions of one release line; it cannot be combined with "
 1296             print(f"component         {printable(a.component)}")
```
### `packages`
```
  773         """The folders of the package this project builds: the one its name says, the ones
  787             elif len(parts) == 3 and parts[0] in ("src", "lib") and parts[1] not in NOT_PACKAGES:
  788                 tops.add(parts[0] + "/" + parts[1])
```
### `imported_from`
```
  549     """The sibling module a package's __init__ imports `attr` from: `from .mod import attr`."""
  555         return None
```
### `diagnose_start`
```
 2112     """What a bug report needs and a user cannot be asked to look up: the versions involved and
 2118         git_version = "git could not be run"
```
### `working_tree_state`
```
 1151     """(dirty, why it was not checked). `git status` would run a clean filter named in the
 1155         return None, "not checked: the local git config could not be read"
```
### `check_globs`
```
  186     """Refuse, by name, a glob that cannot be compiled, or that holds a range written backwards
  197                 raise Refusal(f"invalid {what} glob {g!r}: {e}")
```
### `local_config`
```
  210     """[(key, value)] of the repository's own git config, or None when it cannot be read."""
  213         return None
```
### `python`
```
  738             return "Cargo.toml", "cargo"
  756             return "setup.cfg", "cfg"
```
### `publication_points`
```
  825     """→ ([(commit, date, name)] oldest first, how many there were before the cut, tags that do
  838             continue
```
### `version_written_at_publish`
```
 1913     """§32: (path, line number, line) of a workflow step at this commit that writes the package version
 1917             continue
```
### `version_name_hint`
```
  893     """`--version-file` read with the default pattern, which reads `version` in lower case: when the
  906     return ""
```
### `bounded_search`
```
  394     """The label a pattern captures, or None. A pattern that is not built in is matched in a child
  408         raise Refusal(f"the version pattern {pattern!r} could not be evaluated")
```
### `no_label_refusal`
```
  958     """The refusal for no label, naming the files the rules read one directory below the root.
  968         doc = None
```
### `contradicted`
```
 1085         """Sources found by the rules that were read at tags carrying a version and agree with none.
```
### `unique_keys`
```
 1097     """A JSON object, refused when a key appears twice: the last one would win in silence."""
```
### `git_bytes`
```
  115     """Output of a git command. A failure is a Refusal, or None when may_fail — never empty output."""
```
### `print_coverage`
```
 2174         print(f"  {c['points_label_contradicted']} took their label from "
```
### `printable`
```
  142     """Text safe to print: control, format and invisible characters are written as escapes."""
```
### `matches`
```
  156     """`*` crosses folders; a leading `**/` matches zero or more of them."""
```
### `explain`
```
 1184     """Which paths differ between the first closure a label named and each of the others.
```
### `excluded`
```
  163     """Never part of a closure. `**/name` patterns are matched against a file's own name, so a
```
### `excluded_folders`
```
  172     """The excluded folders a path lies in, when only folders exclude it; None when a file pattern
```
### `find`
```
  692         """(path, how), (TAG_SOURCE, None), or None."""
```
### `git_version`
```
  204         raise Refusal(f"cannot run git: {e.strerror or e}")
```
### `__init__`
```
  233             raise Refusal(f"cannot run git: {e.strerror or e}")
```
### `close`
```
  245             self.proc.kill()
```
### `root_tree`
```
  268             raise Refusal(f"commit {commit[:12]} names no tree")
```
### `children`
```
  272         """[(name, kind, object id)] of one tree object, in git's own order."""
```
### `attribute`
```
  792         """`pkg.attr`: in the module itself, or in the sibling module its __init__ imports it from."""
```
### `release_numbers`
```
  811     """The leading numbers of a version, as text without leading zeros: `py-v2.052.0-rc0` →
```
### `entries`
```
  300         """[(path, kind, object id)] for every file and submodule pointer at a commit — the
```
### `prerelease_key`
```
 1838     """One spelling of a pre-release (PEP 440 normalization): `2.9.0-rc0`, `2.9.0rc0` and
```
### `tag_label`
```
  818     """The version a tag-derived build gives a tag: an optional `word-` prefix and a leading `v`
```
### `tag_prefix`
```
 1845     """The part of a tag's name before its version: `helper` in `helper-v0.5`, `@s/b` in `@s/b@1.2`."""
```
### `text`
```
  325                 self.text_bytes -= len(self.texts.popitem(last=False)[1])
```
### `flush`
```
 1354         pass
```
### `scm_derived`
```
 1872     """A pyproject.toml whose build takes the version from the tag (rule 2 of docs/LABELS.md)."""
```
### `prefixed_source`
```
 1882     """§29: the manifest a tag's prefix names, as (path, how); None when the prefix is absent, generic,
```
### `brought_in`
```
  347         """A glob that names every excluded folder the path lies in brings it in (O13, §29)."""
```
### `modes`
```
  355         """path -> mode at a commit, read with `git ls-tree` only when --modes asks for it."""
```
### `version_key`
```
  868     """`--label-equality version`: `v1`, `1.0` and `1.0.0` are one label; `1.1` and `1.10` are two.
```
### `member_map`
```
  365         """path -> (kind, object id[, mode]) of the members; the mode only with --modes."""
```
### `label_twins`
```
  881     """Labels counted apart that `--label-equality version` would make one (`1.0`, `1.0.0`), when
```
### `ids`
```
  370         """(short id, full id, number of files). The short id is the 16-hex value of every version
```
### `closure_hash`
```
  387     """The 16-hex closure of 0.3.0 onward and the number of files in it. Kept under its historical
```
### `drift_mechanisms`
```
  910     """How each label in drift came about, from the names of the tags that first carry its states
```
### `match_on_stdin`
```
  412     """The child side of bounded_search. Reads {"pattern", "text"}, prints {"label"}."""
```
### `tag_versions`
```
  930     """The versions a tag can name, as written: the whole name, without a leading `v`, after a prefix
```
### `label_of`
```
  420     """Group 1; or, when the pattern names groups `part1`, `part2`, …, their non-empty values in
```
### `plausible`
```
  434     """A label is a version someone wrote: it has a digit, and it is not a format template
```
### `root_has_source`
```
  981     """Whether a commit has, at its root, a file the rules read. The rules read nothing else, so a
```
### `inherits_workspace_version`
```
  474     """`version.workspace = true` or `version = { workspace = true }` in a member's [package]."""
```
### `read_published`
```
  990     """`--published`: one version per line; blank lines and `#` lines ignored. → (versions, sha256)."""
```
### `attribute_value`
```
  492     """`name = "..."` at the start of a line, the string being the whole right-hand side."""
```
