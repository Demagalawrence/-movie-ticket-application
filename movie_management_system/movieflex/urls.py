from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # Authentication
    path('register/', views.register, name='register'),
    path('movies/add/', views.movie_add, name='movie_add'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Movies
    path('movies/', views.movie_list, name='movie_list'),

    # Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/add/<str:movie_id>/', views.booking_add, name='booking_add'),
    path('bookings/payment/<int:booking_id>/', views.booking_payment, name='booking_payment'),
    path('bookings/payment/success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('bookings/payment/cancel/<int:booking_id>/', views.payment_cancel, name='payment_cancel'),
    path('bookings/ticket/<int:booking_id>/', views.ticket_download, name='ticket_download'),

    # Admin approval
    path('admin/bookings/', views.admin_booking_queue, name='admin_booking_queue'),
    path('admin/bookings/approve/<int:booking_id>/', views.admin_booking_approve, name='admin_booking_approve'),
    path('admin/bookings/reject/<int:booking_id>/', views.admin_booking_reject, name='admin_booking_reject'),
]
