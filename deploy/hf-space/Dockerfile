FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///./khetse.db \
    DEMO_MODE=true \
    LOG_LEVEL=INFO \
    CORS_ORIGINS=*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# HF Spaces runs containers as UID 1000; make the workdir writable for SQLite.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# Create the schema (portable create_all), seed the labelled demo dataset, serve.
CMD ["sh", "-c", "python -c \"from app.db.session import Base, engine; import app.models; Base.metadata.create_all(engine)\" && python -m app.db.seed && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
