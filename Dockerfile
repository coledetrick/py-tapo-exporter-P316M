FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tapo_p316m_exporter.py .

EXPOSE 9499
CMD ["python", "tapo_p316m_exporter.py"]
