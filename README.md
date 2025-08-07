# Alemeno System - Production Deployment

A Django-based backend application with PostgreSQL, Redis, and Celery for background processing.

## 🚀 Live Deployment

The application is currently running on **AWS EC2**:

- **Swagger API Documentation**: http://54.206.127.17:8000/api/docs/
- **Backend APIs**: http://54.206.127.17:8000/

## 📋 Prerequisites

- Docker & Docker Compose installed
- Environment variables configured (see `.env.example`)
- Ports 8000, 5432, 6379 available

## ⚙️ Environment Setup

Create a `.env` file in the project root:

```env
# Database
DB_NAME=alemeno_db
DB_USER=alemeno_user
DB_PASSWORD=your_secure_password
DB_HOST=db
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=your_long_secret_key_here
DEBUG=False

# Redis
REDIS_HOST=redis
```

## 🐳 Quick Start

1. **Clone and navigate to project**:
   ```bash
   git clone https://github.com/genin6382/Alemeno-Internship-Task.git
   cd Alemeno-Internship-Task
   ```

2. **Start all services**:
   ```bash
   docker compose up --build
   ```

3. **Check status**:
   ```bash
   docker compose ps
   ```

4. **View logs**:
   ```bash
   docker compose logs -f backend
   ```

5. **Access the application**:
   - API: http://localhost:8000/
   - Swagger: http://localhost:8000/api/docs/

## 🏗️ Architecture

- **Backend**: Django REST Framework
- **Database**: PostgreSQL
- **Cache**: Redis  
- **Task Queue**: Celery
- **Web Server**: Gunicorn
- **Containerization**: Docker Compose

## 📊 Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | Django application |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache & task queue |
| celery | - | Background task worker |

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
docker-compose exec backend python manage.py test

# Run specific app tests
docker-compose exec backend python manage.py test customer

# Run with coverage
docker-compose exec backend coverage run --source='.' manage.py test
docker-compose exec backend coverage report
```

## 📝 API Documentation

### Swagger UI
Interactive API documentation available at `/api/docs/`

## 🔧 Management Commands

```bash
# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Run migrations
docker-compose exec backend python manage.py migrate

# Collect static files
docker-compose exec backend python manage.py collectstatic

# Load initial data
docker-compose exec backend python manage.py ingest_initial_data
```

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8000/health/
```

### Container Status
```bash
docker-compose ps
docker-compose logs backend
docker-compose logs celery
```

### Database Access
```bash
docker-compose exec db psql -U alemeno_user -d alemeno_db
```


## 🚨 Troubleshooting

### Common Issues

**Containers won't start:**
```bash
docker-compose down -v
docker-compose up --build
```

**Migration errors:**
```bash
docker-compose exec backend python manage.py migrate --fake-initial
```

**Permission errors:**
```bash
sudo chown -R $USER:$USER ./data
```

### Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs celery
docker-compose logs db
```

## 🔐 Security

- Environment variables stored in `.env` file (not committed)
- Database passwords are encrypted
- Redis protected by internal network
- Debug mode disabled in production

## 📞 Support

- Check logs: `docker-compose logs [service]`
- Database issues: Verify `.env` credentials
- Port conflicts: Ensure ports 8000, 5432, 6379 are available
- Permission issues: Check file ownership and Docker daemon access

## 🏷️ Version

Current version: v1.0.0

---
