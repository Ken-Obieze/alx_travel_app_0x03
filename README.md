# ALX Travel App - Background Task Management with Celery & RabbitMQ

A Django REST API application with integrated background task processing using Celery and RabbitMQ for email notifications and payment processing.

## Project Overview

This project implements a travel booking platform with asynchronous task processing for:
- Email notifications for booking confirmations
- Payment confirmation emails
- Payment failure notifications
- Background processing of time-intensive operations

## Technology Stack

- **Backend**: Django 4.2.7 + Django REST Framework
- **Database**: MySQL 8.0+
- **API Documentation**: drf-spectacular (OpenAPI 3.0)
- **Task Queue**: Celery 5.3.4
- **Message Broker**: RabbitMQ
- **Payment Gateway**: Chapa API
- **Email**: SMTP (Gmail)

## Features

✅ User authentication and management  
✅ Property listings management  
✅ Booking system with email notifications  
✅ Payment processing with Chapa  
✅ Asynchronous email sending via Celery  
✅ Background task management with RabbitMQ  
✅ Task retry mechanism for failed emails  
✅ Task monitoring and logging  

## Architecture

```
User Action → Django View → Celery Task (delay()) → RabbitMQ → Celery Worker → Email Sent
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- MySQL 8.0+
- RabbitMQ 3.8+
- Chapa Account

### 2. Install RabbitMQ

#### On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin (optional)
sudo rabbitmq-plugins enable rabbitmq_management

# Access management UI at: http://localhost:15672
# Default credentials: guest/guest
```

#### On macOS:
```bash
brew install rabbitmq
brew services start rabbitmq
```

#### On Windows:
Download from https://www.rabbitmq.com/download.html

### 3. Clone and Setup

```bash
git clone https://github.com/ken-obieze/alx_travel_app_0x03.git
cd alx_travel_app_0x03

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Environment Configuration

Create `.env` file:

```env
# Database
DB_NAME=alx_travel_db
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//

# Email (Gmail example)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Chapa
CHAPA_SECRET_KEY=your-chapa-test-key
CHAPA_PUBLIC_KEY=your-chapa-public-key
CHAPA_WEBHOOK_SECRET=your-webhook-secret

# Frontend
FRONTEND_URL=http://localhost:3000
```

**Note for Gmail**: 
1. Enable 2-factor authentication
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the app password in `EMAIL_HOST_PASSWORD`

### 5. Database Setup

```bash
# Create database
mysql -u root -p
CREATE DATABASE alx_travel_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed database
python manage.py seed --users 20 --listings 50 --bookings 100
```

### 6. Running the Application

You need **THREE** terminal windows:

#### Terminal 1: Django Server
```bash
source venv/bin/activate
python manage.py runserver
```

#### Terminal 2: Celery Worker
```bash
source venv/bin/activate
celery -A alx_travel_app worker --loglevel=info

# On Windows, use:
celery -A alx_travel_app worker --loglevel=info --pool=solo
```

#### Terminal 3: Celery Beat (Optional - for scheduled tasks)
```bash
source venv/bin/activate
celery -A alx_travel_app beat --loglevel=info
```

## Celery Configuration

### Celery Architecture

```python
# alx_travel_app/celery.py
app = Celery('alx_travel_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### Task Definition

```python
# listings/tasks.py
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation_email(self, booking_id):
    try:
        # Send email logic
        pass
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)
```

### Task Execution

```python
# listings/views.py
def perform_create(self, serializer):
    booking = serializer.save(user=self.request.user)
    
    # Execute task asynchronously
    send_booking_confirmation_email.delay(str(booking.booking_id))
```

## Email Notification Flow

### 1. Booking Creation Email
**Triggered when**: User creates a new booking

```python
POST /api/bookings/
{
  "property_id": "uuid",
  "start_date": "2025-12-01",
  "end_date": "2025-12-05"
}
```

**What happens**:
1. Booking is created in database
2. Task is queued in RabbitMQ: `send_booking_confirmation_email.delay(booking_id)`
3. Celery worker picks up the task
4. Email is sent to user
5. Task completion logged

### 2. Booking Confirmation Email
**Triggered when**: Host confirms a booking

```python
POST /api/bookings/{booking_id}/confirm/
```

### 3. Payment Confirmation Email
**Triggered when**: Payment is successfully completed

```python
POST /api/payments/verify/{tx_ref}/
```

## Testing Background Tasks

### Test 1: Check RabbitMQ Status

```bash
# Check if RabbitMQ is running
sudo systemctl status rabbitmq-server

# Check queues
sudo rabbitmqctl list_queues
```

### Test 2: Monitor Celery Worker

```bash
# In Celery worker terminal, you should see:
[INFO/MainProcess] Connected to amqp://guest:**@localhost:5672//
[INFO/MainProcess] celery@hostname ready.
```

### Test 3: Create a Booking and Verify Email

```bash
# 1. Create a booking
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "property_id": "your-property-uuid",
    "start_date": "2025-12-01",
    "end_date": "2025-12-05"
  }'

# 2. Check Celery worker terminal for task execution:
#    [INFO/ForkPoolWorker-1] Task listings.tasks.send_booking_confirmation_email
#    [INFO/ForkPoolWorker-1] Task completed successfully

# 3. Check your email inbox for confirmation
```

### Test 4: Test Task Retry Mechanism

Temporarily configure wrong email settings to see retry:

```python
# In .env, set wrong password
EMAIL_HOST_PASSWORD=wrong-password

# Create booking - task will fail and retry 3 times
# Check Celery logs for retry attempts
```

## Monitoring & Debugging

### View Celery Logs

```bash
# Check application logs
tail -f logs/celery.log

# Check Django logs
tail -f logs/django.log
```

### RabbitMQ Management UI

Access: http://localhost:15672  
Credentials: guest/guest

Features:
- View queues and messages
- Monitor task rates
- Check worker connections
- View task statistics

### Flower (Celery Monitoring Tool - Optional)

```bash
pip install flower
celery -A alx_travel_app flower

# Access: http://localhost:5555
```

## Celery Task Configuration

### Task Settings (in settings.py)

```python
# Task serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Task result expires after 24 hours
CELERY_RESULT_EXPIRES = 86400

# Maximum retries for failed tasks
CELERY_TASK_MAX_RETRIES = 3

# Retry delay (seconds)
CELERY_TASK_DEFAULT_RETRY_DELAY = 60

# Task time limits
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes
```

### Task Routing

```python
# Route specific tasks to specific queues
app.conf.task_routes = {
    'listings.tasks.send_booking_confirmation_email': {'queue': 'emails'},
    'listings.tasks.send_payment_confirmation_email': {'queue': 'emails'},
}
```

## API Endpoints

### Bookings (with email notifications)

```http
POST /api/bookings/              # Create booking → triggers email
GET /api/bookings/               # List bookings
GET /api/bookings/{id}/          # Get booking details
POST /api/bookings/{id}/confirm/ # Confirm booking → triggers email
```

### Payments (with email notifications)

```http
POST /api/payments/initiate/        # Initiate payment
GET /api/payments/verify/{tx_ref}/  # Verify payment → triggers email
```

## Troubleshooting

### Issue: Celery worker not starting

**Solution**:
```bash
# Check RabbitMQ is running
sudo systemctl status rabbitmq-server

# Check broker URL in .env
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```

### Issue: Emails not sending

**Solutions**:
1. Check email configuration in `.env`
2. For Gmail, use App Password (not regular password)
3. Check Celery worker logs for errors
4. Test email settings:
```python
python manage.py shell
from django.core.mail import send_mail
send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

### Issue: Tasks stuck in queue

**Solution**:
```bash
# Purge all queued tasks
celery -A alx_travel_app purge

# Restart worker
# Ctrl+C to stop, then restart
celery -A alx_travel_app worker --loglevel=info
```

### Issue: Database connection in Celery tasks

**Solution**: Celery workers maintain separate database connections. Ensure your database settings allow multiple connections.

## Project Structure

```
alx_travel_app_0x03/
├── alx_travel_app/
│   ├── __init__.py           # Celery app initialization
│   ├── settings.py           # Celery & RabbitMQ config
│   ├── celery.py             # Celery configuration
│   └── urls.py
├── listings/
│   ├── models.py
│   ├── views.py              # Triggers email tasks
│   ├── serializers.py
│   ├── tasks.py              # Celery tasks (EMAIL LOGIC HERE)
│   ├── services.py           # Chapa integration
│   └── permissions.py
├── logs/
│   ├── django.log
│   └── celery.log
├── requirements.txt
├── .env
└── README.md
```

## Production Considerations

1. **Use a process manager** (Supervisor/systemd) for Celery workers
2. **Set up monitoring** (Flower, Prometheus, Sentry)
3. **Configure proper logging** and log rotation
4. **Use environment-specific settings** (separate .env for prod)
5. **Set up SSL/TLS** for RabbitMQ in production
6. **Configure email rate limiting** to avoid spam filters
7. **Set task timeouts** to prevent hanging tasks
8. **Use connection pooling** for database
9. **Monitor queue sizes** and scale workers accordingly

## Performance Tips

1. **Use task priorities** for critical emails
2. **Implement task rate limiting** to avoid overwhelming email servers
3. **Use connection pooling** for RabbitMQ
4. **Monitor memory usage** of Celery workers
5. **Set appropriate worker concurrency**:
   ```bash
   celery -A alx_travel_app worker --concurrency=4
   ```

## Security Notes

- Never commit `.env` file
- Use strong RabbitMQ credentials in production
- Enable SSL for RabbitMQ connections
- Implement task authentication if exposing Celery via HTTP
- Sanitize email content to prevent injection attacks

## License

This project is part of the ALX Software Engineering program.

## Contact

For questions or issues, please contact the development team.