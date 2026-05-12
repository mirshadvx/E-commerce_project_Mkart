# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     gcc libpq-dev && \
#     rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# RUN python manage.py collectstatic --noinput

# CMD ["gunicorn", "mkart.wsgi:application", "--bind", "0.0.0.0:8000"]

# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV DJANGO_SETTINGS_MODULE=mkart.mkart.settings.prod   # ← Fixed

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     gcc \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# COPY mkart/requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# # Collectstatic
# RUN DATABASE_URL=sqlite:///dummy.db python mkart/manage.py collectstatic --noinput --clear

# EXPOSE 8000

# CMD ["gunicorn", "mkart.mkart.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]




FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory to /app/mkart (where manage.py is)
WORKDIR /app/mkart

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY mkart/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire mkart directory (including manage.py)
COPY mkart/ .

# Expose port
EXPOSE 8000

# Run migrations, collectstatic, and start Gunicorn
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn mkart.wsgi:application --bind 0.0.0.0:8000"]