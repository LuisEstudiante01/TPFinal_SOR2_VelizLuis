#!/usr/bin/env python3
"""Quick diagnostic used on 2026-11-19 (incident I4): tokens/s of Ollama with
0 to 24 competitors and with competitor nice 5, 10 and 19, 16 tokens each.
Not a measurement: no repetitions. Run from the directory of run_matrix.py.

The original run used two lists of conditions (see obsidian/08 Incidencias.md, I4):
  --set first   0, 6, 12, 24 competitors and 12 with nice 10 and 19
  --set second  1, 2, 3 competitors and 12 with nice 5
"""
import argparse
import http.client
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_matrix as m  # noqa: E402

SETS = {
    "first": [("comp0", 0, 0), ("comp6", 6, 0), ("comp12", 12, 0), ("comp24", 24, 0),
              ("nice10", 12, 10), ("nice19", 12, 19)],
    "second": [("comp1", 1, 0), ("comp2", 2, 0), ("comp3", 3, 0), ("comp12_n5", 12, 5)],
}


def gen(n):
    body = {"model": "llama3.2:3b", "prompt": "[diag %f] Explain what a CPU scheduler does." % time.time(),
            "stream": False, "keep_alive": "10m",
            "options": {"temperature": 0, "seed": 1, "num_predict": n, "num_ctx": 4096}}
    c = http.client.HTTPConnection("127.0.0.1", m.DOCKER_PORT, timeout=1200)
    c.request("POST", "/api/generate", json.dumps(body), {"Content-Type": "application/json"})
    resp = c.getresponse()
    d = json.loads(resp.read())
    c.close()
    if resp.status != 200:
        raise RuntimeError("HTTP %d" % resp.status)
    return d["eval_count"] / (d["eval_duration"] / 1e9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", choices=sorted(SETS), default="first")
    args = ap.parse_args()
    m.stop_competitors()
    try:
        for name, comp, nice in SETS[args.set]:
            cg, _, _ = m.configure_container(None, m.PINNED)
            gen(4)  # load the model before the competitors start
            proc = m.start_competitors(cg, comp, nice, m.PINNED) if comp else None
            t = time.time()
            tps = gen(16)
            m.stop_competitors(cg, proc)
            print("%-9s tok/s=%.2f  (%.0fs)" % (name, tps, time.time() - t), flush=True)
    finally:
        try:
            m.stop_competitors()
        finally:
            m.configure_container(None, m.ALL_CPUS)


if __name__ == "__main__":
    main()
