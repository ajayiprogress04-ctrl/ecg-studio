FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
RUN useradd --create-home ecg && mkdir /data && chown ecg:ecg /data
USER ecg
ENV ECG_DATA_DIR=/data/ecg-jobs
EXPOSE 5000
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "120", "backend.app:app"]
