# Ecommerce

It's a Django-based ecommerce web application with product catalog management, user accounts, cart and wishlist flows, checkout, coupons, offers, wallet support, Razorpay payments, Google OAuth, Cloudinary media storage, and an admin dashboard.

The project is configured for PostgreSQL and includes Docker Compose files for containerized development/production-style deployment with Gunicorn and Nginx.

## Tech Stack

- Python 3.11
- Django 5.0
- PostgreSQL 15
- Docker and Docker Compose
- Gunicorn
- Nginx
- WhiteNoise for static files
- Cloudinary for media uploads
- Razorpay for payments
- Google OAuth via `social-auth-app-django`

## Project Structure

```text
.
|-- README.md
|-- requirements.txt
`-- mkart/
    |-- manage.py
    |-- Dockerfile
    |-- docker-compose.yml
    |-- docker-compose.dev.yml
    |-- nginx/
    |   `-- nginx.conf
    |-- mkart/
    |   |-- settings/
    |   |   |-- dev.py
    |   |   `-- prod.py
    |   |-- urls.py
    |   |-- asgi.py
    |   `-- wsgi.py
    |-- home/
    |-- products/
    |-- Admin/
    `-- static/
```

## Main Features

- Customer registration, login, logout, and Google OAuth login
- Product listing with categories, brands, colors, variants, stock, and images
- Product and category offers
- Cart and wishlist management
- Checkout with saved addresses
- Cash on Delivery, Razorpay, and wallet payment options
- Coupon support with usage limits and minimum purchase rules
- Referral wallet credits
- Order placement, order items, status tracking, cancellation, and returns
- Admin dashboard for products, categories, brands, variants, coupons, offers, users, orders, and sales reports
- Invoice/report generation dependencies included
- Cloudinary-backed product media storage

## Environment Variables

Create or update the environment file at:

```text
mkart/mkart/.env
```

Example:

```env
SECRET_KEY=your-django-secret-key
DJANGO_SETTINGS_MODULE=mkart.settings.dev

POSTGRES_DB=mkart
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mnbmnb
POSTGRES_HOST=db

RESEND_API_KEY=your-resend-api-key
RESEND_FROM_EMAIL="Timexo <noreply@your-domain.com>"

RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret

CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your-google-client-id
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-google-client-secret
```

For production, `mkart.settings.prod` expects a `DATABASE_URL` value:

```env
DATABASE_URL=postgres://postgres:mnbmnb@timexo-db:5432/mkart
DJANGO_SETTINGS_MODULE=mkart.settings.prod
```

## Run With Docker

From the project root:

```bash
cd mkart
docker compose -f docker-compose.dev.yml up --build
```

The development Compose file starts:

- `web`: Django/Gunicorn application
- `db`: PostgreSQL database
- `nginx`: reverse proxy exposed on port `80`

Open the app at:

```text
http://localhost/
```

Run migrations:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

Create a superuser:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Collect static files:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput
```

Stop containers:

```bash
docker compose -f docker-compose.dev.yml down
```

Stop containers and remove database/static volumes:

```bash
docker compose -f docker-compose.dev.yml down -v
```

## Production-Style Docker Compose

The `docker-compose.yml` file uses:

- `timexo-web`
- `timexo-db`
- external Docker network named `server-network`
- production settings via `mkart.settings.prod`

Create the external network before starting it:

```bash
docker network create server-network
```

Then run:

```bash
cd mkart
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f timexo-web
```

## Run Locally Without Docker

Install PostgreSQL locally and create a database named `mkart`, then from the project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r mkart/requirements.txt
```

Set your local environment variables. For local PostgreSQL, use:

```env
POSTGRES_DB=mkart
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mnbmnb
POSTGRES_HOST=localhost
DJANGO_SETTINGS_MODULE=mkart.settings.dev
```

Run the app:

```bash
cd mkart
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Useful Commands

```bash
# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create admin user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test
```

Docker equivalents:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
docker compose -f docker-compose.dev.yml exec web python manage.py test
```

## Application URLs

- Storefront: `/`
- Django admin: `/admin/`
- Custom admin panel: `/admin_panel/`
- Google OAuth routes: `/auth/`
