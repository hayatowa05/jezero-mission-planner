# Lander terminal, hosted. Works on Hugging Face Spaces (Docker), Render, Fly.io, Railway, any Docker host.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    HOST=0.0.0.0 PORT=7860 PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Download the real Jezero DEM and pre-render the map at BUILD time, so the live server starts quickly.
RUN python prebuild.py

EXPOSE 7860
CMD ["python", "app.py"]
