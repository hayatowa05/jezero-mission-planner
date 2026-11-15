# Lander terminal on Netlify

Netlify hosts static pages. It cannot run the path finder (a Python server holding the 90 MB elevation model in memory).
So the setup is two parts:

    browser ──► Netlify (the terminal page)  ──forwards /mission/*, /ai/*──►  Python server (path finder)
    HUD on Netlify ──► "Re-download mission" ──► https://<terminal-site>.netlify.app/mission.json

## 1. Host the Python server (once)
Follow DEPLOY.md, Option A (Hugging Face Space) or B (any Docker host). You end up with an https address such as
`https://yourname-jezero.hf.space`. Check that `https://<that address>/healthz` shows `{"ok": true, ...}`.
Do NOT set `APP_PASSWORD` on it for this setup (the password prompt does not pass cleanly through Netlify).

## 2. Build the Netlify folder
    python make_netlify.py https://yourname-jezero.hf.space
This creates `netlify_site/` with `index.html` (the terminal) and `_redirects` (the forwarding rules).

## 3. Put it on Netlify
Drag the `netlify_site` folder onto https://app.netlify.com/drop (or create a site from it in your Netlify account).
Open the site address: the lander terminal loads and plans routes through the Python server.

## 4. Link the HUD
In the HUD (finalmarshud.netlify.app): Menu → Base link → enter `<terminal-site>.netlify.app` → **Re-download mission**.
It fetches the latest planned route. The **HUD mission** file button also still works.

## Limits
- "Connect" (live push over WebSocket) does not work through Netlify, which does not forward WebSockets. To use the live link,
  enter the Python server's own address in the HUD instead of the Netlify one.
- Netlify stops forwarded requests after roughly 26 seconds. Normal routes take a few seconds; a very long route on the real
  map, or the first request while the server is still starting, can hit that limit. Retry once the server is warm.
- Not tested end to end: this was prepared without access to a Netlify or hosting account.

## Same site as the HUD (optional)
To have one address for both, copy `netlify_site/index.html` into the HUD's site as `planner/index.html` and add the lines of
`netlify_site/_redirects` to the HUD site's `_redirects`. The terminal is then at `finalmarshud.netlify.app/planner/` and the
HUD's Base link is simply its own address.
