FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY ml_study.py profile_api.py /app/ml/
RUN touch /app/ml/__init__.py
CMD ["python", "-m", "ml.profile_api"]
