from django.contrib import admin
from .models import User, Booking, Review, Listing, BookingStatus, PaymentMethod, Payment, Message

# Register your models here.
admin.site.register([User, Booking, Review, Listing, BookingStatus, PaymentMethod, Payment, Message])