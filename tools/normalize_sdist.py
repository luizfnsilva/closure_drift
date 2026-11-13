#!/usr/bin/env python3
"""Rewrite an sdist so that its bytes depend only on its content and SOURCE_DATE_EPOCH.

setuptools writes the builder's uid, user name and checkout mtimes into the tar headers, and the
current time into the gzip header. Two builds of the same tag then give the same files and a
different sha256 (measured on 1.8.0). This keeps every member's name, mode and bytes, and sets:
member order sorted by name, mtime = SOURCE_DATE_EPOCH, uid = gid = 0, no user or group names,
gzip mtime 0, no file name in the gzip header.

    SOURCE_DATE_EPOCH=... python3 tools/normalize_sdist.py dist/*.tar.gz

Standard library only.
"""
import gzip
import io
import os
import sys
import tarfile


def normalize(path, epoch):
    with tarfile.open(path, "r:gz") as src:
        members = [(m, src.extractfile(m).read() if m.isfile() else None) for m in src.getmembers()]
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=tarfile.PAX_FORMAT) as dst:
        for m, data in sorted(members, key=lambda x: x[0].name):
            m.mtime = epoch
            m.uid = m.gid = 0
            m.uname = m.gname = ""
            m.pax_headers = {}
            dst.addfile(m, io.BytesIO(data) if data is not None else None)
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
        gz.write(out.getvalue())
    with open(path, "wb") as fh:
        fh.write(raw.getvalue())


def main(argv):
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch or not epoch.isdigit():
        raise SystemExit("SOURCE_DATE_EPOCH is not set to an integer: refusing to guess a date.")
    if not argv:
        raise SystemExit("usage: normalize_sdist.py SDIST...")
    for path in argv:
        normalize(path, int(epoch))
        print("normalized", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
