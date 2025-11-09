"""
Views for the listings app.
"""
from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import models
from django.conf import settings
import logging
from .payment_serializers import (
    PaymentInitiateSerializer, 
    PaymentResponseSerializer,
    PaymentVerifyResponseSerializer,
    PaymentListSerializer
)
from .tasks import send_payment_confirmation_email, send_payment_failed_email
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from .models import Listing, Booking, Review, User, BookingStatus, Payment, PaymentMethod
from .serializers import (
    ListingSerializer, 
    ListingCreateUpdateSerializer,
    BookingSerializer, 
    BookingCreateSerializer,
    ReviewSerializer,
    UserSerializer,
    UserCreateSerializer,
    PaymentSerializer
)
from .permissions import IsOwnerOrReadOnly, IsHostOrReadOnly
from .services import ChapaService
from .tasks import send_payment_confirmation_email, send_payment_failed_email
import logging

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    Provides CRUD operations for users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'user_id'

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Allow anyone to register (create), but require authentication for other actions
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile
        Endpoint: GET /api/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def listings(self, request, user_id=None):
        """
        Get all listings for a specific user
        Endpoint: GET /api/users/{user_id}/listings/
        """
        user = self.get_object()
        listings = Listing.objects.filter(host=user)
        serializer = ListingSerializer(listings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def bookings(self, request, user_id=None):
        """
        Get all bookings for a specific user
        Endpoint: GET /api/users/{user_id}/bookings/
        """
        user = self.get_object()
        bookings = Booking.objects.filter(user=user)
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class ListingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Listing model.
    Provides full CRUD operations for property listings.
    
    List: GET /api/listings/
    Create: POST /api/listings/
    Retrieve: GET /api/listings/{property_id}/
    Update: PUT /api/listings/{property_id}/
    Partial Update: PATCH /api/listings/{property_id}/
    Delete: DELETE /api/listings/{property_id}/
    """
    queryset = Listing.objects.all().select_related('host').prefetch_related('reviews')
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsHostOrReadOnly]
    lookup_field = 'property_id'
    
    # Add filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'price_per_night']
    search_fields = ['name', 'description', 'location']
    ordering_fields = ['price_per_night', 'created_at', 'name']
    ordering = ['-created_at']  # Default ordering

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action in ['create', 'update', 'partial_update']:
            return ListingCreateUpdateSerializer
        return ListingSerializer

    def perform_create(self, serializer):
        """
        Set the host to the current user when creating a listing
        """
        serializer.save(host=self.request.user)

    def get_queryset(self):
        """
        Optionally filter listings by price range
        """
        queryset = super().get_queryset()
        
        # Filter by minimum price
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price_per_night__gte=min_price)
        
        # Filter by maximum price
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price_per_night__lte=max_price)
        
        return queryset

    @action(detail=True, methods=['get'])
    def reviews(self, request, property_id=None):
        """
        Get all reviews for a specific listing
        Endpoint: GET /api/listings/{property_id}/reviews/
        """
        listing = self.get_object()
        reviews = listing.reviews.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_review(self, request, property_id=None):
        """
        Add a review to a listing
        Endpoint: POST /api/listings/{property_id}/add_review/
        Body: {"rating": 5, "comment": "Great place!"}
        """
        listing = self.get_object()
        
        # Check if user has already reviewed this property
        if Review.objects.filter(property=listing, user=request.user).exists():
            return Response(
                {'error': 'You have already reviewed this property'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=listing, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def bookings(self, request, property_id=None):
        """
        Get all bookings for a specific listing (host only)
        Endpoint: GET /api/listings/{property_id}/bookings/
        """
        listing = self.get_object()
        
        # Only allow host to see all bookings
        if request.user != listing.host:
            return Response(
                {'error': 'Only the host can view all bookings for this property'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_listings(self, request):
        """
        Get all listings for the current user
        Endpoint: GET /api/listings/my_listings/
        """
        listings = Listing.objects.filter(host=request.user)
        serializer = self.get_serializer(listings, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Booking model.
    Provides full CRUD operations for bookings.
    
    List: GET /api/bookings/
    Create: POST /api/bookings/
    Retrieve: GET /api/bookings/{booking_id}/
    Update: PUT /api/bookings/{booking_id}/
    Partial Update: PATCH /api/bookings/{booking_id}/
    Delete: DELETE /api/bookings/{booking_id}/
    """
    queryset = Booking.objects.all().select_related('property', 'user', 'status')
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'booking_id'
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status_info__status_name', 'property']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        """
        Filter bookings to show only user's own bookings
        unless they are the property host
        """
        user = self.request.user
        
        # Get bookings where user is either the guest or the host
        return Booking.objects.filter(
            models.Q(user=user) | models.Q(property__host=user)
        ).distinct()

    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a booking
        and trigger email notification
        """
        booking = serializer.save(user=self.request.user)
        
        # Import here to avoid circular imports
        from .tasks import send_booking_confirmation_email
        
        # Trigger email task asynchronously using Celery
        send_booking_confirmation_email.delay(str(booking.booking_id))
        
        logger.info(f"Booking created: {booking.booking_id}. Email task queued.")

    @action(detail=True, methods=['post'])
    def confirm(self, request, booking_id=None):
        """
        Confirm a booking (host only)
        Endpoint: POST /api/bookings/{booking_id}/confirm/
        """
        booking = self.get_object()
        
        # Only the host can confirm bookings
        if request.user != booking.property.host:
            return Response(
                {'error': 'Only the host can confirm bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update booking status
        confirmed_status = BookingStatus.objects.get(status_name='confirmed')
        booking.status = confirmed_status
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, booking_id=None):
        """
        Cancel a booking
        Endpoint: POST /api/bookings/{booking_id}/cancel/
        """
        booking = self.get_object()
        
        # Only the guest or host can cancel
        if request.user not in [booking.user, booking.property.host]:
            return Response(
                {'error': 'You do not have permission to cancel this booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update booking status
        cancelled_status = BookingStatus.objects.get(status_name='cancelled')
        booking.status = cancelled_status
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """
        Get all bookings for the current user (as guest)
        Endpoint: GET /api/bookings/my_bookings/
        """
        bookings = Booking.objects.filter(user=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def hosting_bookings(self, request):
        """
        Get all bookings for properties hosted by the current user
        Endpoint: GET /api/bookings/hosting_bookings/
        """
        bookings = Booking.objects.filter(property__host=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Review model.
    Provides CRUD operations for reviews.
    """
    queryset = Review.objects.all().select_related('property', 'user')
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'review_id'

    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a review
        """
        serializer.save(user=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Review model.
    Provides CRUD operations for reviews.
    """
    queryset = Review.objects.all().select_related('property', 'user')
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'review_id'

    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a review
        """
        serializer.save(user=self.request.user)


class PaymentInitiateView(generics.CreateAPIView):
    """
    API View to initiate payment via Chapa
    POST /api/payments/initiate/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentInitiateSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Initiate a payment for a booking
        
        Request body:
        {
            "booking_id": "uuid-here"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking_id = serializer.validated_data['booking_id']
        
        try:
            # Get the booking
            booking = Booking.objects.select_related('property', 'user').get(
                booking_id=booking_id
            )
            
            # Verify the user owns this booking
            if booking.user != request.user:
                return Response(
                    {'error': 'You do not have permission to pay for this booking'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if payment already exists and is completed
            existing_payment = Payment.objects.filter(
                booking=booking,
                payment_status='completed'
            ).first()
            
            if existing_payment:
                return Response(
                    {'error': 'This booking has already been paid for'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create payment method
            payment_method, _ = PaymentMethod.objects.get_or_create(
                method_name='chapa'
            )
            
            # Initialize Chapa service
            chapa_service = ChapaService()
            
            # Prepare callback and return URLs
            callback_url = f"{request.build_absolute_uri('/api/payments/webhook/')}"
            return_url = f"{settings.FRONTEND_URL}/bookings/{booking_id}/payment-success"
            
            # Initialize payment with Chapa
            payment_response = chapa_service.initialize_payment(
                booking=booking,
                user=request.user,
                callback_url=callback_url,
                return_url=return_url
            )
            
            if payment_response['status'] == 'error':
                return Response(
                    {'error': payment_response['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create payment record
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                payment_status='pending',
                chapa_reference=payment_response['tx_ref'],
                payment_method=payment_method,
                currency='ETB',
                customer_email=request.user.email,
                customer_first_name=request.user.first_name or '',
                customer_last_name=request.user.last_name or '',
                customer_phone=request.user.phone_number or ''
            )
            
            logger.info(f"Payment initiated: {payment.payment_id}")
            
            # Create response data
            response_data = {
                'status': 'success',
                'message': 'Payment initialized successfully',
                'payment_id': str(payment.payment_id),
                'checkout_url': payment_response['checkout_url'],
                'tx_ref': payment_response['tx_ref']
            }
            
            headers = self.get_success_headers(serializer.data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your payment'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentVerifyView(generics.RetrieveAPIView):
    """
    API View to verify payment status
    GET /api/payments/verify/{tx_ref}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentVerifyResponseSerializer
    lookup_field = 'tx_ref'
    lookup_url_kwarg = 'tx_ref'
    
    def get_queryset(self):
        return Payment.objects.select_related('booking')
    
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        
        # Verify user has permission
        if obj.booking.user != self.request.user:
            raise PermissionDenied("You do not have permission to verify this payment")
            
        return obj
    
    def get(self, request, *args, **kwargs):
        """
        Verify a payment transaction
        """
        payment = self.get_object()
        tx_ref = self.kwargs.get(self.lookup_url_kwarg)
        
        try:
            # Initialize Chapa service and verify payment
            chapa_service = ChapaService()
            verification_result = chapa_service.verify_payment(tx_ref)
            
            if verification_result['status'] == 'error':
                return Response(
                    {'error': verification_result['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract payment data from verification
            payment_data = verification_result.get('data', {})
            chapa_status = payment_data.get('status', '').lower()
            
            # Update payment status
            if chapa_status == 'success':
                payment.payment_status = 'completed'
                payment.transaction_id = payment_data.get('reference')
                payment.save()
                
                # Update booking status to confirmed
                confirmed_status, _ = BookingStatus.objects.get_or_create(
                    status_name='confirmed'
                )
                payment.booking.status = confirmed_status
                payment.booking.save()
                
                # Send confirmation email (async with Celery)
                send_payment_confirmation_email.delay(str(payment.payment_id))
                
                logger.info(f"Payment completed: {payment.payment_id}")
                
            elif chapa_status == 'failed':
                payment.payment_status = 'failed'
                payment.save()
                
                # Send failure email
                send_payment_failed_email.delay(str(payment.payment_id))
                
                logger.warning(f"Payment failed: {payment.payment_id}")
            
            # Return updated payment status
            payment_serializer = PaymentResponseSerializer(payment, context=self.get_serializer_context())
            return Response({
                'status': 'success',
                'payment': payment_serializer.data,
                'chapa_status': chapa_status,
                'verification_data': payment_data
            })
            
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return Response(
                {'error': 'An error occurred while verifying the payment'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentWebhookView(APIView):
    """
    API View to handle Chapa webhook notifications
    POST /api/payments/webhook/
    """
    permission_classes = [AllowAny]  # Chapa will call this endpoint
    serializer_class = None  # No serializer needed for webhook
    
    def post(self, request):
        """
        Handle webhook notification from Chapa
        """
        try:
            webhook_data = request.data
            tx_ref = webhook_data.get('tx_ref')
            
            if not tx_ref:
                return Response(
                    {'error': 'tx_ref is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process webhook using Chapa service
            chapa_service = ChapaService()
            result = chapa_service.handle_webhook(webhook_data)
            
            if result['status'] == 'error':
                logger.error(f"Webhook processing error: {result['message']}")
                return Response(
                    {'error': result['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get payment record
            payment = Payment.objects.select_related('booking').get(
                chapa_reference=tx_ref
            )
            
            # Update payment status based on webhook
            payment_status = result.get('payment_status', '').lower()
            
            if payment_status == 'success':
                payment.payment_status = 'completed'
                payment.transaction_id = webhook_data.get('reference')
                payment.save()
                
                # Update booking status
                confirmed_status, _ = BookingStatus.objects.get_or_create(
                    status_name='confirmed'
                )
                payment.booking.status = confirmed_status
                payment.booking.save()
                
                # Send confirmation email
                send_payment_confirmation_email.delay(str(payment.payment_id))
                
                logger.info(f"Webhook: Payment completed {payment.payment_id}")
                
            elif payment_status == 'failed':
                payment.payment_status = 'failed'
                payment.save()
                
                # Send failure email
                send_payment_failed_email.delay(str(payment.payment_id))
                
                logger.warning(f"Webhook: Payment failed {payment.payment_id}")
            
            return Response({
                'status': 'success',
                'message': 'Webhook processed successfully'
            })
            
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for tx_ref: {tx_ref}")
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return Response(
                {'error': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentListView(generics.ListAPIView):
    """
    API View to list payments for the authenticated user
    GET /api/payments/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentListSerializer
    
    def get_queryset(self):
        return Payment.objects.filter(
            booking__user=self.request.user
        ).select_related('booking', 'booking__property').order_by('-payment_date')


class PaymentDetailView(generics.RetrieveAPIView):
    """
    API View to get payment details
    GET /api/payments/{payment_id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentResponseSerializer
    queryset = Payment.objects.all()
    lookup_field = 'payment_id'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'booking', 'booking__property', 'booking__user'
        )
        
    def retrieve(self, request, *args, **kwargs):
        try:
            payment = self.get_object()
            # Verify user has permission
            if payment.booking.user != request.user:
                return Response(
                    {'error': 'You do not have permission to view this payment'},
                    status=status.HTTP_403_FORBIDDEN
                )
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )