FROM python:3.12-slim
RUN pip install --no-cache-dir shapely==2.0.7
COPY data /data
COPY app.py /app.py
ENV MAPIT_LOCAL_DATA=/data MAPIT_UPSTREAM=https://global.mapit.mysociety.org MAPIT_PORT=8080
USER nobody
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "-u", "/app.py"]
