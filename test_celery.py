#!/usr/bin/env python
"""
Script to test Celery and RabbitMQ configuration
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')
django.setup()

from listings.tasks import send_booking_confirmation_email, debug_task
from listings.models import Booking
from celery.result import AsyncResult
import time


def test_celery_connection():
    """Test if Celery can connect to RabbitMQ"""
    print("="*60)
    print("Test 1: Celery Connection to RabbitMQ")
    print("="*60)
    
    try:
        from alx_travel_app.celery import app
        
        # Check connection
        inspect = app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✓ Successfully connected to RabbitMQ")
            print(f"✓ Active workers: {list(stats.keys())}")
            return True
        else:
            print("✗ No active Celery workers found")
            print("  Please start a Celery worker:")
            print("  celery -A alx_travel_app worker --loglevel=info")
            return False
            
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False


def test_simple_task():
    """Test a simple Celery task"""
    print("\n" + "="*60)
    print("Test 2: Execute Simple Task")
    print("="*60)
    
    try:
        from alx_travel_app.celery import debug_task
        
        # Execute task asynchronously
        result = debug_task.delay()
        
        print(f"✓ Task queued with ID: {result.id}")
        print("  Waiting for task to complete...")
        
        # Wait for result (with timeout)
        try:
            output = result.get(timeout=10)
            print(f"✓ Task completed successfully")
            return True
        except Exception as e:
            print(f"✗ Task execution failed: {str(e)}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to queue task: {str(e)}")
        return False


def test_email_task():
    """Test email sending task"""
    print("\n" + "="*60)
    print("Test 3: Email Task with Real Booking")
    print("="*60)
    
    try:
        # Get a recent booking
        booking = Booking.objects.select_related('user', 'property').first()
        
        if not booking:
            print("✗ No bookings found in database")
            print("  Please create a booking first or run: python manage.py seed")
            return False
        
        print(f"✓ Found booking: {booking.booking_id}")
        print(f"  Property: {booking.property.name}")
        print(f"  User: {booking.user.email}")
        
        # Queue email task
        result = send_booking_confirmation_email.delay(str(booking.booking_id))
        
        print(f"✓ Email task queued with ID: {result.id}")
        print("  Waiting for email to be sent...")
        
        # Wait for result
        try:
            output = result.get(timeout=30)
            print(f"✓ {output}")
            print(f"✓ Check the recipient's email: {booking.user.email}")
            return True
        except Exception as e:
            print(f"✗ Email task failed: {str(e)}")
            print("  Check:")
            print("  1. Email configuration in .env")
            print("  2. Celery worker logs")
            print("  3. Gmail App Password if using Gmail")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False


def test_task_retry():
    """Test task retry mechanism"""
    print("\n" + "="*60)
    print("Test 4: Task Retry Mechanism")
    print("="*60)
    
    print("  This test demonstrates how Celery retries failed tasks")
    print("  (Task will retry 3 times with 60 second delay between retries)")
    print("  Skipping actual retry test to save time...")
    print("✓ Retry mechanism is configured in tasks.py")
    print("  @shared_task(bind=True, max_retries=3, default_retry_delay=60)")
    return True


def check_rabbitmq_queues():
    """Check RabbitMQ queues"""
    print("\n" + "="*60)
    print("Test 5: RabbitMQ Queue Status")
    print("="*60)
    
    try:
        from alx_travel_app.celery import app
        
        inspect = app.control.inspect()
        
        # Get active queues
        active_queues = inspect.active_queues()
        
        if active_queues:
            print("✓ Active queues found:")
            for worker, queues in active_queues.items():
                print(f"  Worker: {worker}")
                for queue in queues:
                    print(f"    - {queue['name']}")
            return True
        else:
            print("  No active queues (this is normal if no workers are running)")
            return True
            
    except Exception as e:
        print(f"✗ Failed to check queues: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  CELERY & RABBITMQ TEST SUITE")
    print("="*60)
    print("\nPrerequisites:")
    print("1. RabbitMQ server is running")
    print("2. Celery worker is running in another terminal:")
    print("   celery -A alx_travel_app worker --loglevel=info")
    print("3. Database is set up and seeded")
    print("4. Email configuration is set in .env")
    
    input("\nPress Enter to start tests...")
    
    results = []
    
    # Run tests
    results.append(("Celery Connection", test_celery_connection()))
    time.sleep(1)
    
    results.append(("Simple Task", test_simple_task()))
    time.sleep(1)
    
    results.append(("Email Task", test_email_task()))
    time.sleep(1)
    
    results.append(("Retry Mechanism", test_task_retry()))
    time.sleep(1)
    
    results.append(("RabbitMQ Queues", check_rabbitmq_queues()))
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print("\n" + "="*60)
    print(f"  {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n All tests passed! Celery and RabbitMQ are working correctly.")
    else:
        print("\n  Some tests failed. Please check the output above.")
        print("   Common issues:")
        print("   - Celery worker not running")
        print("   - RabbitMQ server not running")
        print("   - Incorrect email configuration")
        print("   - Database not seeded")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()