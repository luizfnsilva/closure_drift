#!/usr/bin/env python3
"""Write STUDY.md and collisions.tsv from the stored reports of both runs. Nothing is measured here.

    python3 tools/study/make_report.py
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(folder):
    return {r["repository"]: r for r in (json.loads(f.read_text(encoding="utf-8"))
                                         for f in sorted((folder / "results").glob("*.json")))}


def selection():
    rows = []
    for line in (HERE / "selection.tsv").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            rank, project, repo, status = line.split("\t")
            if status == "selected":
                rows.append((int(rank), project, repo))
    return rows


def sha_of(folder):
    return (folder / "results.tsv").read_text(encoding="utf-8").splitlines()[0].split()[-1]


def outcome(row):
    return "no label found" if row["outcome"] == "refused" else row["outcome"]


def main():
    one, two, picked = load(HERE / "run1"), load(HERE), selection()
    c1, c2 = Counter(outcome(r) for r in one.values()), Counter(outcome(r) for r in two.values())
    decided = c2["clean"] + c2["drift"]
    reports = {k: v["report"] for k, v in two.items() if v["outcome"] in ("clean", "drift")}
    scanned = sum(r["publication_points_scanned"] for r in reports.values())
    compared = sum(r["publication_points_compared"] for r in reports.values())
    from_tag = sorted(k for k, r in reports.items()
                      if two[k]["outcome"] == "clean" and set(r["label_sources"]) == {"(the tag)"})
    families = sorted(k for k, r in reports.items() if r.get("tag_families"))
    moved = sorted((repo, outcome(one[repo]), outcome(two[repo])) for _, _, repo in picked
                   if outcome(one[repo]) != outcome(two[repo]))

    # one line per (label, tag) of every collision
    lines = ["# repository\tmeasured_at_head\tlabel\ttag (date)\tclosure\tclosure_id\tlabel read from"]
    labels_in_drift = 0
    for _, _, repo in picked:
        row = two[repo]
        if row["outcome"] != "drift":
            continue
        rep = row["report"]
        for label, states in rep["drift"].items():
            labels_in_drift += 1
            for key, where in states.items():
                lines.append("\t".join([repo, rep["stamp"]["measured_at_head"], json.dumps(label, ensure_ascii=True)[1:-1],
                                        json.dumps(where, ensure_ascii=True)[1:-1], key, rep["closure_ids"][key],
                                        "; ".join(sorted(rep["label_sources"]))]))
    (HERE / "collisions.tsv").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    order = ["clean", "drift", "no label found", "inconclusive", "no_labels"]
    md = ["# Do Python projects' version labels always identify one code state?", "",
          "The 100 most-downloaded PyPI projects with a public repository, measured with `closure_drift`",
          "at its defaults. The selection rule and the method were written down before the first run",
          "([`PREREGISTRATION.md`](PREREGISTRATION.md)); the list ([`selection.tsv`](selection.tsv)) was",
          "committed before any measurement. No repository was tuned, added or dropped.", "",
          "**Reproduce it, look at the cases, and say where the method is wrong.**", "",
          "## Result", "",
          "| outcome | run 1 | run 2 |", "|---|---|---|"]
    for o in order:
        if c1[o] or c2[o]:
            md.append("| %s | %d | %d |" % ("`%s`" % o if o != "no label found" else o, c1[o], c2[o]))
    md += ["| **total** | 100 | 100 |", "",
           "**Run 2: a version label names more than one code state in %d of the %d repositories where a"
           % (c2["drift"], decided),
           "determination was reached, and in %d of all 100.** The %d undecided stay in the denominator"
           % (c2["drift"], 100 - decided),
           "of the second figure; they are listed below.", "",
           "- %d of %d tags scanned in the decided repositories were compared; the rest declare no version."
           % (compared, scanned),
           "- %d version labels are in drift in all; every one is a line in [`collisions.tsv`](collisions.tsv)."
           % labels_in_drift,
           "- In %d of the %d `clean` repositories the version is derived from the tag itself. There"
           % (len(from_tag), c2["clean"]),
           "  `clean` holds by construction: it says only that no two tags give the same version.",
           "- In %d of the %d in drift the colliding tags belong to different families (a monorepo"
           % (len(families), c2["drift"]),
           "  releasing several packages from one version file): %s."
           % ", ".join("`%s`" % f for f in families), "",
           "## Why there are two runs", "",
           "Run 1 said more about the tool than about the projects: it read the version from one file",
           "chosen at HEAD, so %d repositories gave no label and several others were read from a constant"
           % c1["no label found"],
           "that is not the released version. The detector was changed for that — the source is resolved at",
           "each tag, declared pointers are followed, and a version derived from the tag is read from the",
           "tag — with the change written down before run 2 (`PREREGISTRATION.md`, run 2). Run 1 is kept,",
           "every row, in [`run1/`](run1/). %d repositories changed outcome between the runs:" % len(moved), "",
           "| repository | run 1 | run 2 |", "|---|---|---|"]
    md += ["| `%s` | %s | %s |" % m for m in moved]
    md += ["", "## Limits", "",
           "- Defaults only. The default closure globs are a guess about what determines each project's",
           "  output; a collision here means two tags declare one version and differ in files those globs",
           "  match.",
           "- A collision is not a judgement. Common causes seen in the table: a tag created without",
           "  bumping the version, maintenance-branch markers such as `7.x`, and tag families.",
           "- The 400 most recent tags are scanned. Labels are compared as written.",
           "- One person measured, on one machine. Nobody outside has reproduced it yet.",
           "- No maintainer was contacted before publication.", "",
           "## Reproduce", "",
           "```bash",
           "python3 tools/study/run_study.py /some/empty/dir     # clones, measures, deletes — about 40 minutes",
           "python3 tools/study/make_report.py                    # rebuilds this page and collisions.tsv",
           "```", "",
           "One collision, by hand — any line of `collisions.tsv`:", "",
           "```bash",
           "git clone https://github.com/psf/requests && cd requests",
           "closure-drift --compare v2.16.0 v2.16.1     # both declare 2.16.0; the paths that differ are listed",
           "```", "",
           "Detector: run 2 sha256 `%s`, run 1 `%s`." % (sha_of(HERE), sha_of(HERE / "run1")),
           "The reports as emitted are in [`results/`](results/) and [`run1/results/`](run1/results/).", "",
           "## Every repository", "",
           "| rank | project | repository | run 1 | run 2 | tags compared | labels | in drift | label read from |",
           "|---|---|---|---|---|---|---|---|---|"]
    for rank, project, repo in picked:
        rep = two[repo].get("report") or {}
        cov = ("%s of %s" % (rep["publication_points_compared"], rep["publication_points_scanned"])
               if "publication_points_scanned" in rep else "")
        md.append("| %d | %s | `%s` | %s | %s | %s | %s | %s | %s |" % (
            rank, project, repo, outcome(one[repo]), outcome(two[repo]), cov, rep.get("labels", ""),
            rep.get("labels_covering_multiple_closures", ""),
            ", ".join("`%s`" % s for s in sorted(rep.get("label_sources", {}))[:3])))
    if (HERE / "run3" / "results").is_dir():
        md += [""] + run3_section(picked)
    later = HERE / "posthoc.md"            # a later, exploratory reading: appended, never mixed in
    if later.exists():
        md += ["", later.read_text(encoding="utf-8").rstrip()]
    (HERE / "STUDY.md").write_bytes(("\n".join(md) + "\n").encode("utf-8"))
    print("run 1:", dict(c1), "| run 2:", dict(c2), "| collisions:", labels_in_drift, "labels,", len(lines) - 1, "lines")


def run3_section(picked):
    """Run 3: each clone measured with 0.10.0 and with 0.9.1 (PREREGISTRATION.md, "Run 3")."""
    new, old = load(HERE / "run3"), load(HERE / "run3-baseline")
    cn, co = Counter(outcome(r) for r in new.values()), Counter(outcome(r) for r in old.values())
    order = ["clean", "drift", "incomplete", "no label found", "inconclusive", "no_labels"]
    out = ["## Run 3 — detector 0.10.0 against 0.9.1, on the same clones", "",
           "Run on GitHub's runners on 2026-10-05; each repository was cloned once and measured with both",
           "detectors, so what differs between the two columns is the detector, not the repositories.", "",
           "| outcome | 0.9.1 | 0.10.0 |", "|---|---|---|"]
    for o in order:
        if cn[o] or co[o]:
            out.append("| %s | %d | %d |" % ("`%s`" % o if o != "no label found" else o, co[o], cn[o]))
    decided = cn["clean"] + cn["drift"]
    out += ["", "**0.10.0: a version label names more than one code state in %d of the %d repositories where"
            % (cn["drift"], decided), "a determination was reached, and in %d of all 100.**" % cn["drift"], "",
            "Repositories whose outcome differs between the two detectors:", ""]
    moved = [(repo, outcome(old[repo]), outcome(new[repo]), new[repo].get("report") or {})
             for _, _, repo in picked if outcome(old[repo]) != outcome(new[repo])]
    for repo, a, b, rep in moved:
        out.append("- `%s`: %s → %s (%s of %s tags compared)" % (
            repo, a, b, rep.get("publication_points_compared"), rep.get("publication_points_scanned")))
    if not moved:
        out.append("- none")
    out += ["", "Detectors: 0.10.0 sha256 `%s`, 0.9.1 `%s`."
            % (sha_of(HERE / "run3"), sha_of(HERE / "run3-baseline")),
            "The released 0.10.0 script differs from the one that measured this run in the text of one refusal",
            "and in how much memory it keeps (`tests/PREREGISTRATION.md` §10, amendments 4 and 5); on the 60",
            "generated repositories of the property suite and six public ones, the two print the same report."]
    return out


if __name__ == "__main__":
    main()
