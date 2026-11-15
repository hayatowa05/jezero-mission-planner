# Putting the lander terminal online

The app is one Python process (`python app.py`) that serves the page and the planner. Hosting it means running that
process on a machine with a public address. Nothing in the code needs changing per host; it is configured with
environment variables:

| Variable | Meaning | Default |
|---|---|---|
| `HOST` | address to listen on (`0.0.0.0` = reachable from outside) | `127.0.0.1` |
| `PORT` | port (most hosts set this for you) | `8050` |
| `APP_PASSWORD` | if set, the whole site asks for this password (user name `mission`, change with `APP_USER`) | none (open) |
| `MAX_BODY_BYTES` | largest request accepted | 1 000 000 |

`/healthz` is always open (for the host's health check). When `HOST` is not local, the old classic-planner write routes
are switched off. If you host publicly without `APP_PASSWORD`, anyone with the link can run the planner, and each plan
uses real CPU, so set a password unless you want it open.

## Option A - Hugging Face Space (easiest, free tier exists)
1. Create an account at huggingface.co, then **New Space** -> SDK **Docker** -> blank template.
2. Upload every file from this folder (or push this GitHub repo to the Space). The `Dockerfile` is already here.
3. Add this line at the very top of `README.md` in the Space, so it knows the port:
   ```
   ---
   title: Jezero Lander Terminal
   sdk: docker
   app_port: 7860
   ---
   ```
4. Space -> Settings -> **Variables and secrets** -> new *secret* `APP_PASSWORD`.
5. The build downloads the 90 MB DEM and renders the map (several minutes). When it says *Running*, the Space URL is your site.

Notes: the free disk is wiped when the Space restarts, but the build step regenerates everything, so that is fine.
Whether the free CPU tier is enough for the real 20 m map (about 22 million cells) is NOT verified: if the build or
first plan dies with an out-of-memory error, choose a bigger hardware tier in Settings.

## Option B - any Docker host (Render, Fly.io, Railway, a VPS)
```
docker build -t lander-terminal .
docker run -p 7860:7860 -e APP_PASSWORD=choose-one lander-terminal
```
Point the host at port 7860 (or set `PORT`). Give it at least 4 GB RAM to be safe for the real map.

## Option C - quick temporary link from your own PC
Keep running locally (`python app.py`), then in a second window:
```
cloudflared tunnel --url http://localhost:8050
```
(or `ngrok http 8050`). You get a public https link while your PC and the program stay on. Set `APP_PASSWORD` first:
`set APP_PASSWORD=choose-one` (Windows cmd) before `python app.py`.

## No Docker, plain Python host
`pip install -r requirements.txt && python prebuild.py && HOST=0.0.0.0 python app.py`

## Not tested here
The Docker image itself could not be built in the sandbox I worked in (no Docker). The server was tested directly with
`HOST=0.0.0.0 PORT=7860 APP_PASSWORD=...`: health check, 401 without or with a wrong password, 200 with the right one,
oversize request rejected (413), classic write routes hidden.
