FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home labuser
COPY --chown=labuser:labuser lab ./lab
COPY --chown=labuser:labuser web ./web
COPY --chown=labuser:labuser catalog.json run.py ./
RUN mkdir runtime && chown labuser:labuser runtime
USER labuser
EXPOSE 8765
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8765"]
