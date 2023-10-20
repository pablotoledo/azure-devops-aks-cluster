FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY polling.py .

CMD ["python", "-u", "polling.py"]
