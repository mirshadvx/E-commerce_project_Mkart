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

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     gcc \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .

# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 8000

# CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn mkart.wsgi:application --bind 0.0.0.0:8000"]

# Collectstatic with dummy DB (good practice)

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mkart.settings.prod

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY mkart/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collectstatic
RUN DATABASE_URL=sqlite:///dummy.db python mkart/manage.py collectstatic --noinput --clear

EXPOSE 8000

CMD ["gunicorn", "mkart.mkart.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]