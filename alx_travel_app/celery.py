"""
Celery configuration for alx_travel_app project with RabbitMQ
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

# Create Celery app
app = Celery('alx_travel_app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery to use RabbitMQ
app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    print(f'Request: {self.request!r}')


# Optional: Define task routes for different queues
app.conf.task_routes = {
    'listings.tasks.send_booking_confirmation_email': {'queue': 'emails'},
    'listings.tasks.send_payment_confirmation_email': {'queue': 'emails'},
    'listings.tasks.send_payment_failed_email': {'queue': 'emails'},
}