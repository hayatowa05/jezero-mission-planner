"""
Planner -> Mars EVA HUD mission file.

The HUD (teammates' web app) accepts, by "Load mission file", GET /mission.json or a WebSocket message:

    {"type": "mission", "name": str,
     "waypoints": [{"x": east_m, "y": north_m, "name": str}, ...],      # at least 2; the first one is the start
     "hazards":   [{"x": east_m, "y": north_m, "name": str, "r": radius_m}, ...]}

x / y are Site ENU metres from the lander (Perseverance landing site, 18.44463 N 77.45089 E): the same frame as this
planner, so no conversion is needed. The HUD draws a smooth Catmull-Rom curve THROUGH the waypoints, so the waypoints
are chosen here such that this curve stays within `max_dev_m` of the planned route (checked with the HUD's own formula).
Extra keys ("meta") are ignored by the HUD.
"""
import math

import numpy as np


def hud_spline(P):
    """The curve the HUD draws through waypoints P (copied from its setMission: uniform Catmull-Rom, ~1.5 m samples)."""
    P = [tuple(p) for p in P]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        n = max(2, round(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / 1.5))
        t = np.arange(n) / n
        t2, t3 = t * t, t * t * t
        f = lambda a, b, c, d: .5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
        out.append(np.stack([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])], 1))
    out.append(np.array([P[-1]], float))
    return np.concatenate(out)


def _dist_to_polyline(pts, line):
    """Distance from each point to the polyline `line` (n,2)."""
    a, b = line[:-1], line[1:]
    ab = b - a
    L2 = np.maximum((ab ** 2).sum(1), 1e-9)
    best = np.full(len(pts), 1e18)
    for s in range(0, len(pts), 4000):
        p = pts[s:s + 4000, None, :]
        t = np.clip(((p - a) * ab).sum(2) / L2, 0, 1)
        d = np.hypot(*(np.moveaxis(p - (a + t[..., None] * ab), 2, 0)))
        best[s:s + 4000] = d.min(1)
    return best


def _rdp(pts, keep, tol):
    """Douglas-Peucker; indices in `keep` are always kept."""
    n = len(pts)
    mark = np.zeros(n, bool)
    mark[[0, n - 1]] = True
    mark[list(keep)] = True
    anchors = np.flatnonzero(mark)
    stack = list(zip(anchors[:-1], anchors[1:]))
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        L = math.hypot(*ab) or 1e-9
        d = np.abs(ab[0] * (pts[i + 1:j, 1] - a[1]) - ab[1] * (pts[i + 1:j, 0] - a[0])) / L
        k = int(d.argmax())
        if d[k] > tol:
            m = i + 1 + k
            mark[m] = True
            stack += [(i, m), (m, j)]
    return np.flatnonzero(mark)


def build(route_enu, name="Jezero route", fix_stops=(), turn_back=None, hazards=(), start_name="Start", goal_name="Goal",
          max_dev_m=3.0, meta=None):
    """route_enu: [[east, north], ...] dense planned route. fix_stops: [{"enu": [e, n], "method", "duration_s"}].
    turn_back: [e, n] or None. hazards: [{"enu": [e, n], "radius_m": r, "name"?}]. Returns the HUD mission dict."""
    pts = np.asarray(route_enu, float)[:, :2]
    if len(pts) < 2:
        raise ValueError("route needs at least two points")
    seg = np.hypot(*np.diff(pts, axis=0).T)
    pts = pts[np.r_[True, seg > 0.05]]                       # drop repeated points (fix stops repeat a point)
    if len(pts) < 2:
        raise ValueError("route has no length")
    near = lambda e, n: int(np.hypot(pts[:, 0] - e, pts[:, 1] - n).argmin())
    special = {}
    for s in fix_stops:
        special[near(*s["enu"][:2])] = f"Fix stop: {s.get('method', 'position fix')} {int(s.get('duration_s', 60))} s"
    if turn_back is not None:
        k = near(*turn_back[:2])
        if 0 < k < len(pts) - 1 and k not in special:
            special[k] = "Turn-back point"
    # 1) Douglas-Peucker keeps the corners; 2) the HUD's Catmull-Rom curve overshoots where waypoint spacing is uneven,
    #    so add the route point nearest to the worst overshoot until the drawn curve is within max_dev_m of the route.
    idx = list(_rdp(pts, special.keys(), max_dev_m))
    dev = 1e9
    for _ in range(600):
        W = pts[idx]
        curve = hud_spline(W)
        d = _dist_to_polyline(curve, pts)
        dev = float(d.max())
        if dev <= max_dev_m:
            break
        # which waypoint gap does each curve sample belong to (same sampling rule as hud_spline)
        cnt = [max(2, round(math.hypot(*(W[i + 1] - W[i])) / 1.5)) for i in range(len(W) - 1)]
        gap = np.r_[np.repeat(np.arange(len(cnt)), cnt), len(cnt) - 1]
        added = False
        for w in np.argsort(-d):                             # worst sample first; split its gap (or a neighbour's)
            if d[w] <= max_dev_m:
                break
            for g in (int(gap[w]), int(gap[w]) - 1, int(gap[w]) + 1):
                if 0 <= g < len(idx) - 1 and idx[g + 1] - idx[g] >= 2:
                    idx = sorted(set(idx) | {(idx[g] + idx[g + 1]) // 2})
                    added = True
                    break
            if added:
                break
        if not added:
            break
    wps, k = [], 0
    for j, i in enumerate(idx):
        if j == 0:
            nm = start_name
        elif j == len(idx) - 1:
            nm = goal_name
        elif int(i) in special:
            nm = special[int(i)]
        else:
            k += 1
            nm = f"WP {k}"
        wps.append({"x": round(float(pts[i, 0]), 1), "y": round(float(pts[i, 1]), 1), "name": nm})
    hz = [{"x": round(float(h["enu"][0]), 1), "y": round(float(h["enu"][1]), 1),
           "name": h.get("name") or f"Hazard {n + 1}", "r": round(float(h.get("radius_m", 40.0)), 1)}
          for n, h in enumerate(hazards)]
    m = dict(meta or {})
    m.update({"frame": "Site ENU metres; x = east, y = north; origin = lander (18.44463 N, 77.45089 E)",
              "waypoint_count": len(wps), "max_curve_deviation_m": round(dev, 2)})
    return {"type": "mission", "name": name, "waypoints": wps, "hazards": hz, "meta": m}


def from_payload(P, req=None):
    """Build the HUD mission from a planner web payload (mission_web._payload) and the request that produced it."""
    req = req or {}
    shelter = str(P.get("verdict", "")).startswith("SHELTER")
    s0 = P["route"]["enu"][0]
    at_lander = math.hypot(s0[0], s0[1]) < 30
    name = (f"{'SHELTER route' if shelter else 'Jezero ' + P.get('mode', 'walk') + ' route'}: "
            f"{P.get('distance_km', 0):.2f} km, ETA {P.get('eta_min', 0):.0f} min")
    meta = {k: P.get(k) for k in ("mode", "profile", "verdict", "distance_km", "eta_min", "energy_kJ", "risk_score",
                                  "min_return_margin_frac", "predicted_sigma_m") if k in P}
    return build(P["route"]["enu"], name=name, fix_stops=P.get("fix_stop_detail", []),
                 turn_back=None if shelter else P.get("turn_back_point_enu_m"),
                 hazards=req.get("hazards", []), start_name="Lander" if at_lander else "Crew position",
                 goal_name="Lander (shelter)" if shelter else (req.get("goal_name") or "Goal"), meta=meta)
