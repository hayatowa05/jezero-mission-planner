#!/usr/bin/env python3
"""Build the folder to drop on Netlify: the lander terminal page + rules that forward planner requests to the Python server.

    python make_netlify.py https://your-backend.example.com

Creates ./netlify_site/ (index.html, _redirects). Drag that folder onto app.netlify.com/drop, or add it to an existing site.
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("usage: python make_netlify.py https://your-backend-address   (must be https, no trailing path)")
    backend = sys.argv[1].rstrip("/")
    out = os.path.join(HERE, "netlify_site")
    os.makedirs(out, exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "mission_ui.html"), os.path.join(out, "index.html"))
    with open(os.path.join(out, "_redirects"), "w", newline="\n") as f:
        f.write("# Netlify serves index.html; everything the page asks the planner for is forwarded to the Python server.\n"
                f"/mission/*     {backend}/mission/:splat   200\n"
                f"/ai/*          {backend}/ai/:splat        200\n"
                f"/mission.json  {backend}/mission.json     200\n"
                f"/healthz       {backend}/healthz          200\n")
    print(f"Wrote {out}\n  forwarding to {backend}\nNow drag the netlify_site folder onto https://app.netlify.com/drop")


if __name__ == "__main__":
    main()
