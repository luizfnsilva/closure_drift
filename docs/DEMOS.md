# Three demonstrations

Each block is the real output of `closure_drift` on a tiny repository built by
`tools/make_demos.py`. CI rebuilds this page and fails if it differs.

## A · Catch a version-label mistake before publishing

`v1.0.0` is released. A fix is committed and the version file is not touched. Before tagging:

```
$ closure-drift --would-tag
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (1 scanned)

commit            89bb35b525a1
label at HEAD     1.0.0
closure at HEAD   f1c007e78a122ba0

==============================================================
WOULD DRIFT: the label 1.0.0 already names different code at:
      v1.0.0 (2020-01-04)

Tagging this commit would make one label name more than one closure.
Change the version before you tag. To see what differs:
      --compare v1.0.0 HEAD

Publication points: 1 scanned, 1 compared.
(exit 1)
```

After bumping the version:

```
$ closure-drift --would-tag
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (1 scanned)

commit            544194166825
label at HEAD     1.0.1
closure at HEAD   f1c007e78a122ba0

==============================================================
WOULD BE CLEAN: no existing tag declares 1.0.1 with different code.

Publication points: 1 scanned, 1 compared.
(exit 0)
```

## B · Don't just flag drift. Show where it is.

Two tags, `v1.0.0` and `v1.0.1`, and the version file still says `1.0.0` at both.

```
$ closure-drift
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (2 scanned)

label                         closures
--------------------------------------------
1.0.0                                2  <-- names more than one

the same label at two publications, with different code:
  1.0.0
      closure 83825fd0c3aba0dd  first at v1.0.0 (2020-01-04)
      closure d4d72ad2cf6b6828  first at v1.0.1 (2020-01-07)

==============================================================
DRIFT: 1 of 1 labels name more than one closure
at a publication point. The worst covers 2.

An artefact addressed by (input, version) is ambiguous for those labels:
the same address denotes more than one possible output.
Run again with --explain LABEL to list the paths that differ.

Publication points: 2 scanned, 2 compared.
(exit 1)
```

```
$ closure-drift --compare v1.0.0 v1.0.1
A  v1.0.0  (commit cd9b6bf19616)
   label    1.0.0
   closure  83825fd0c3aba0dd   2 file(s)
B  v1.0.1  (commit d237dbf21dbc)
   label    1.0.0
   closure  d4d72ad2cf6b6828   3 file(s)
   changed    src/app.py
   only in B  src/extra.py

==============================================================
DIFFERS UNDER ONE LABEL: both declare 1.0.0, and the code differs
in 2 path(s). If both were published, that label names two things.
(exit 1)
```

## C · A check that cannot tell should say so

Four tags; the first two were made before the project had a version file.

```
$ closure-drift
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (4 scanned)

label                         closures
--------------------------------------------
1.0.0                                1
1.1.0                                1

==============================================================
CLEAN: each of the 2 labels names exactly one closure at publication.
Your version label identifies your code, over the 2 points compared.

Publication points: 4 scanned, 2 compared.
  2 declared no version label there and were not compared.
(exit 0)
```

`clean`, over two of four tags — and the report says so. Asked to be strict, it does not pass:

```
$ closure-drift --strict
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (4 scanned)

label                         closures
--------------------------------------------
1.0.0                                1
1.1.0                                1

==============================================================
INCOMPLETE: no label names more than one closure, but not every publication point
scanned could be compared with confidence. See the counts below.

Publication points: 4 scanned, 2 compared.
  2 declared no version label there and were not compared.
(exit 2)
```

And with one release there is nothing to compare its label with:

```
$ closure-drift
repository        .
version from      VERSION
closure           src/**, lib/**, app/**, *.py, *.js, *.ts, *.rs, *.go, *.java
publication point tags (1 scanned)

label                         closures
--------------------------------------------
1.0.0                                1

==============================================================
INCONCLUSIVE: only one distinct label across the range scanned.

Publication points: 1 scanned, 1 compared.
(exit 2)
```
