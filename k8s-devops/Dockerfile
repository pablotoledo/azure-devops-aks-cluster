FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY polling.py .
COPY pod-agent-ado/pod.yaml pod-agent.yaml

CMD ["python", "-u", "polling.py"]