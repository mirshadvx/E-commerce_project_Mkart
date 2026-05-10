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

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mkart.settings.prod

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# manage.py is inside the mkart/ subdirectory
RUN python mkart/manage.py collectstatic --noinput --settings=mkart.settings.prod

EXPOSE 8000

# gunicorn must also run from repo root, pointing into mkart package
CMD ["gunicorn", "mkart.mkart.wsgi:application", "--bind", "0.0.0.0:8000"]