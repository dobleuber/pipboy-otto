"""Download the raw public gait data used by build_norm.py (about 60 MB).

    python3 fetch_data.py [out_dir]      # default: exo/raw (git-ignored)

Running : figshare 4543435 (Fukuchi et al. 2017) — per-subject processed + force files.
Walking : figshare 5722711 (Fukuchi et al. 2018) — only the treadmill comfortable-speed
          files are pulled out of the 690 MB zip with HTTP range requests.
Both datasets are CC BY 4.0. Needs `curl` on the PATH.
"""
import csv, json, os, struct, subprocess, sys, zlib
from concurrent.futures import ThreadPoolExecutor

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")
RUN_ARTICLE = "https://api.figshare.com/v2/articles/4543435"
WALK_ARTICLE = "https://api.figshare.com/v2/articles/5722711"


def curl(url, *args):
    for _ in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "300", "-L", *args, url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout
    raise SystemExit(f"download failed: {url}")


def save(url, path):
    if not (os.path.exists(path) and os.path.getsize(path) > 1000):
        with open(path, "wb") as f:
            f.write(curl(url))


def fetch_run():
    d = os.path.join(OUT, "run"); os.makedirs(d, exist_ok=True)
    files = json.loads(curl(RUN_ARTICLE))["files"]
    info = max((f for f in files if f["name"] == "RBDSinfo.txt"), key=lambda f: f["id"])
    todo = [(info["download_url"], os.path.join(d, "RBDSinfo.txt"))]
    todo += [(f["download_url"], os.path.join(d, f["name"])) for f in files
             if f["name"].endswith(("processed.txt", "forces.txt"))]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda t: save(*t), todo))
    print("run :", len(todo), "files")


def fetch_walk():
    d = os.path.join(OUT, "walk"); os.makedirs(d, exist_ok=True)
    files = {f["name"]: f for f in json.loads(curl(WALK_ARTICLE))["files"]}
    save(files["WBDSinfo.csv"]["download_url"], os.path.join(d, "WBDSinfo.csv"))
    z = files["WBDSascii.zip"]; url, size = z["download_url"], z["size"]
    rng = lambda a, b: curl(url, "-r", f"{a}-{b}")
    # central directory lives at the end of the zip
    tail = rng(size - 4_000_000, size - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    n_entries, cd_size, cd_off = struct.unpack("<HII", tail[eocd + 10:eocd + 20])
    cd = tail[cd_off - (size - len(tail)):][:cd_size]
    entries, p = [], 0
    for _ in range(n_entries):
        method, = struct.unpack("<H", cd[p + 10:p + 12])
        csize, usize, nlen, elen, clen = struct.unpack("<IIHHH", cd[p + 20:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        entries.append((cd[p + 46:p + 46 + nlen].decode(), method, csize, usize, off))
        p += 46 + nlen + elen + clen
    want = [e for e in entries if e[0].endswith(("walkT05ang.txt", "walkT05knt.txt", "walkT05grf.txt"))]

    def get(e):
        name, method, csize, usize, off = e
        path = os.path.join(d, os.path.basename(name))
        if os.path.exists(path) and os.path.getsize(path) == usize:
            return
        blob = rng(off, off + 30 + 400 + csize)
        nlen, elen = struct.unpack("<HH", blob[26:30])
        data = blob[30 + nlen + elen:30 + nlen + elen + csize]
        raw = zlib.decompress(data, -15) if method == 8 else data
        assert len(raw) == usize, name
        with open(path, "wb") as f:
            f.write(raw)
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(get, want))
    print("walk:", len(want), "files")


if __name__ == "__main__":
    fetch_run(); fetch_walk()
    print("raw data in", os.path.abspath(OUT), "-> now run build_norm.py")
