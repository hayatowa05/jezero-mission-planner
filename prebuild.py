#!/usr/bin/env python3
"""Build-time step for hosting: download the DEM, then render and cache the map layers so the live server starts fast.

    python prebuild.py            # real Jezero DEM (needs internet, ~90 MB)
    python prebuild.py --synthetic
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    synthetic = "--synthetic" in sys.argv
    if not synthetic:
        subprocess.check_call([sys.executable, os.path.join(HERE, "get_data.py")])
    import app
    from mission_web import MissionWeb
    if synthetic:
        import tempfile
        sys.path.insert(0, os.path.join(HERE, "tests"))
        import synth_dem
        p = os.path.join(tempfile.gettempdir(), "jezero_synth", "synth_700.tif")
        if not os.path.exists(p):
            synth_dem.make(p, n=700)
        app.DEM_PATH[0] = p
    mw = MissionWeb(app.terrain, synthetic=synthetic)
    app.terrain(25.0)
    mw.mp                                    # localizability layer + numba compile (cached on disk)
    t0 = time.time()
    mw.layer("base")                         # the big base map, cached to data/mission_layer_*.jpg
    print(f"[prebuild] done in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
