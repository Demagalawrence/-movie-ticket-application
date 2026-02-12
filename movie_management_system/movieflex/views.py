from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Movie, Booking  # MongoDB models setup
from .forms import BookingForm
import qrcode
import stripe
from django.conf import settings
import os
from django.core.mail import EmailMessage
import io
from django.urls import reverse

from django.http import Http404
from mongoengine.errors import DoesNotExist

stripe.api_key = settings.STRIPE_SECRET_KEY

# ---------------- Home section ----------------
def home(request):
    movies = list(Movie.objects())
    return render(request, 'movieflex/home.html', {'movies': movies})


def login_required_mongo(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------- Registration section ----------------
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not email:
            messages.error(request, "Email is required.")
            return redirect('register')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "Username or email already exists.")
            return redirect('register')

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    return render(request, 'movieflex/register.html')

# ---------------- Login section----------------
def user_login(request):
    if request.method == 'POST':
        user_input = request.POST.get('user')  # username or email
        password = request.POST.get('password')

        # Authenticate by username first, then email
        user_obj = User.objects.filter(username=user_input).first() or User.objects.filter(email=user_input).first()

        if user_obj and user_obj.check_password(password):
            django_login(request, user_obj)
            # Store session info for MongoDB access
            request.session['user_id'] = user_obj.id
            request.session['username'] = user_obj.username
            request.session['email'] = user_obj.email
            request.session['role'] = 'admin' if user_obj.is_staff else 'user'
            
            # ✅ Redirect to movie list instead of home
            return redirect('movie_list')
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, 'movieflex/login.html')


# ---------------- Add Movie (Admin Only.) ----------------
@login_required_mongo

def movie_add(request):
    # ✅ Check if user is admin/staff
    if not request.user.is_staff:  # use is_superuser if needed
        messages.error(request, "Unauthorized access! Only admins can add movies.")
        return redirect('movie_list')  # redirect regular users to movie list

    if request.method == 'POST':
        # ✅ collect form data
        title = request.POST.get('title')
        type_ = request.POST.get('type')
        duration = request.POST.get('duration')
        showtimes_str = request.POST.get('showtimes', '')
        showtimes = [s.strip() for s in showtimes_str.split(',') if s.strip()]
        poster_url = request.POST.get('poster')  # field for image URL

        # ✅ handle optional file upload
        poster_file = request.FILES.get('poster_file')
        if poster_file:
            posters_dir = os.path.join(settings.MEDIA_ROOT, 'posters')
            os.makedirs(posters_dir, exist_ok=True)
            filename = poster_file.name
            save_path = os.path.join(posters_dir, filename)
            # Ensure unique filename
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(posters_dir, filename)
                counter += 1
            with open(save_path, 'wb+') as destination:
                for chunk in poster_file.chunks():
                    destination.write(chunk)
            poster_url = settings.MEDIA_URL + 'posters/' + filename

        # ✅ create an auto-increment movie_id
        next_id = (Movie.objects.order_by('-movie_id').first().movie_id + 1) if Movie.objects.count() > 0 else 1

        # ✅ create and save the movie
        movie = Movie(
            movie_id=next_id,
            title=title,
            type=type_,
            duration=int(duration),
            showtimes=showtimes,
            available_seats={time: 30 for time in showtimes},
            poster=poster_url,
        )
        movie.save()

        messages.success(request, f"Movie '{title}' added successfully!")
        return redirect('movie_list')

    # GET request → render add movie form
    return render(request, 'movieflex/movie_add.html')


# ---------------- Edit Movie (Admin Only) ----------------
@login_required_mongo
def movie_edit(request, movie_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access! Only admins can edit movies.")
        return redirect('movie_list')

    try:
        movie = Movie.objects.get(movie_id=int(movie_id))
    except DoesNotExist:
        raise Http404("Movie not found")

    if request.method == 'POST':
        title = request.POST.get('title')
        type_ = request.POST.get('type')
        duration = request.POST.get('duration')
        showtimes_str = request.POST.get('showtimes', '')
        poster_url = request.POST.get('poster')

        # optional new uploaded file overrides URL
        poster_file = request.FILES.get('poster_file')
        if poster_file:
            posters_dir = os.path.join(settings.MEDIA_ROOT, 'posters')
            os.makedirs(posters_dir, exist_ok=True)
            filename = poster_file.name
            save_path = os.path.join(posters_dir, filename)
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(posters_dir, filename)
                counter += 1
            with open(save_path, 'wb+') as destination:
                for chunk in poster_file.chunks():
                    destination.write(chunk)
            poster_url = settings.MEDIA_URL + 'posters/' + filename

        new_showtimes = [s.strip() for s in showtimes_str.split(',') if s.strip()]

        movie.title = title
        movie.type = type_
        movie.duration = int(duration) if duration else None
        movie.showtimes = new_showtimes
        movie.poster = poster_url

        # Rebuild available_seats baseline for listed showtimes
        booked_map = getattr(movie, 'booked_seats', {}) or {}
        movie.available_seats = {st: max(0, 30 - len(booked_map.get(st, []))) for st in new_showtimes}

        movie.save()
        messages.success(request, f"Movie '{title}' updated successfully!")
        return redirect('movie_list')

    # Prefill values for form
    context = {
        'movie': movie,
        'initial_showtimes': ', '.join(movie.showtimes or []),
    }
    return render(request, 'movieflex/movie_edit.html', context)


# ---------------- Delete Movie (Admin Only) ----------------
@login_required_mongo
def movie_delete(request, movie_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access! Only admins can delete movies.")
        return redirect('movie_list')

    try:
        movie = Movie.objects.get(movie_id=int(movie_id))
    except DoesNotExist:
        raise Http404("Movie not found")

    if request.method == 'POST':
        title = movie.title
        movie.delete()
        messages.info(request, f"Movie '{title}' deleted.")
        return redirect('movie_list')

    return render(request, 'movieflex/movie_delete_confirm.html', {'movie': movie})


# ---------------- Logout ----------------
@login_required
def user_logout(request):
    django_logout(request)
    return redirect('login')

# ---------------- Movie List ----------------
@login_required_mongo
def movie_list(request):
    # Query params for search & filter
    q = (request.GET.get('q') or '').strip()
    selected_genre = (request.GET.get('genre') or '').strip()

    qs = Movie.objects
    if q:
        qs = qs(title__icontains=q)
    if selected_genre and selected_genre.lower() != 'all':
        qs = qs(type=selected_genre)

    movies = qs.all()

    # Distinct genre list for filter dropdown
    try:
        genres = sorted([g for g in (Movie.objects.distinct('type') or []) if g])
    except Exception:
        genres = []
    for movie in movies:
        # Normalize available_seats to a dict for safe template rendering
        showtimes = list(getattr(movie, 'showtimes', []) or [])
        booked_map = getattr(movie, 'booked_seats', {}) or {}
        avail = getattr(movie, 'available_seats', None)

        normalized = {}
        if isinstance(avail, dict):
            # Start from existing dict and fill any missing showtimes with defaults
            normalized.update(avail)
            for st in showtimes:
                if st not in normalized:
                    booked = booked_map.get(st, []) if isinstance(booked_map, dict) else []
                    normalized[st] = max(0, 30 - len(booked))
        else:
            # Build fresh availability from booked seats or default capacity
            for st in showtimes:
                booked = booked_map.get(st, []) if isinstance(booked_map, dict) else []
                normalized[st] = max(0, 30 - len(booked))

        # Assign normalized dict to the instance for the template to use
        movie.available_seats = normalized
        movie.seats_list = [(st, normalized.get(st, 0)) for st in showtimes]
    return render(request, 'movieflex/movie_list.html', {
        'movies': movies,
        'genres': genres,
        'q': q,
        'selected_genre': selected_genre or 'all',
    })

# ---------------- Booking List ----------------
@login_required_mongo
def booking_list(request):
    bookings = list(Booking.objects(user_id=request.user.id))
    # Map movie_id -> title
    movie_ids = [b.movie_id for b in bookings]
    movies = {m.movie_id: m for m in Movie.objects(movie_id__in=movie_ids)} if movie_ids else {}
    # Attach transient fields for template
    for b in bookings:
        m = movies.get(b.movie_id)
        b.movie_title = m.title if m else f"Movie #{b.movie_id}"
        b.status_label = 'Pending' if b.payment_status == 'Pending' else ('Confirmed' if b.payment_status == 'Paid' else b.payment_status)
    return render(request, 'movieflex/booking_list.html', {'bookings': bookings})

# ---------------- Add Booking ----------------
@login_required_mongo

def booking_add(request, movie_id):
    # Fetch movie safely using MongoEngine
    try:
        movie = Movie.objects.get(movie_id=int(movie_id))
    except DoesNotExist:
        raise Http404("Movie not found")

    # Prepare showtime choices for the form
    showtime_choices = [(s, s) for s in getattr(movie, 'showtimes', [])]

    if request.method == 'POST':
        form = BookingForm(request.POST)
        form.fields['showtime'].choices = showtime_choices

        if form.is_valid():
            showtime = form.cleaned_data['showtime']
            seats_requested = form.cleaned_data['seats']  # already a cleaned list

            # Handle booked seats map
            booked = movie.booked_seats.get(showtime, [])
            overlap = set(seats_requested) & set(booked)
            if overlap:
                form.add_error('seats', f"Seats already booked: {', '.join(overlap)}")
            else:
                # Create Booking document
                booking = Booking(
                    booking_id=Booking.objects.count() + 1,
                    user_id=request.user.id,
                    movie_id=movie.movie_id,
                    seats_list=seats_requested,
                    seats_booked=len(seats_requested),
                    showtime=showtime,
                    payment_status='Pending'
                )
                booking.save()

                # Update movie booked seats
                movie.booked_seats.setdefault(showtime, []).extend(seats_requested)
                movie.save()
                return redirect('booking_list')
    else:
        form = BookingForm()
        form.fields['showtime'].choices = showtime_choices

    return render(request, 'movieflex/booking_form.html', {
        'form': form,
        'movie': movie,
        'booked_map': getattr(movie, 'booked_seats', {})
    })


# ---------------- Payment ----------------
@login_required_mongo
def booking_payment(request, booking_id):
    booking = Booking.objects(booking_id=booking_id, user_id=request.user.id).first()
    if not booking:
        raise Http404("Booking not found")

    if request.method == "POST":
        # Create a Stripe Checkout Session
        try:
            movie = Movie.objects(movie_id=booking.movie_id).first()
            unit_amount = 1000  # $10.00 per seat in cents
            success_url = request.build_absolute_uri(
                reverse('payment_success', kwargs={'booking_id': booking.booking_id})
            ) + "?session_id={CHECKOUT_SESSION_ID}"
            cancel_url = request.build_absolute_uri(
                reverse('payment_cancel', kwargs={'booking_id': booking.booking_id})
            )

            session = stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"{movie.title if movie else 'Movie'} ({booking.showtime})",
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': booking.seats_booked,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={'booking_id': str(booking.booking_id)},
            )
            return redirect(session.url)
        except Exception as e:
            messages.error(request, f"Payment setup failed: {e}")
            return redirect('booking_payment', booking_id=booking.booking_id)

    # GET: show summary with correct totals
    movie = Movie.objects(movie_id=booking.movie_id).first()
    total_amount_dollars = booking.seats_booked * 10  # $10 per seat
    return render(request, 'movieflex/payment.html', {
        'booking': booking,
        'movie': movie,
        'total_amount_dollars': total_amount_dollars,
    })


# ---------------- Stripe Checkout Success/Cancel ----------------
@login_required_mongo
def payment_success(request, booking_id):
    booking = Booking.objects(booking_id=booking_id, user_id=request.user.id).first()
    if not booking:
        raise Http404("Booking not found")
    # In production, verify session/payment via webhook or retrieve Session
    booking.payment_status = 'Paid'
    booking.approval_status = 'Pending'
    booking.save()
    messages.success(request, "Payment successful. Awaiting admin approval.")
    return redirect('booking_list')


@login_required_mongo
def payment_cancel(request, booking_id):
    messages.info(request, "Payment was cancelled.")
    return redirect('booking_payment', booking_id=booking_id)


# ---------------- Admin Approval ----------------
@login_required_mongo
def admin_booking_queue(request):
    if not request.user.is_staff:
        raise Http404()
    pending = Booking.objects(payment_status='Paid', approval_status='Pending')
    # Attach movie titles
    ids = [b.movie_id for b in pending]
    movies = {m.movie_id: m for m in Movie.objects(movie_id__in=ids)} if ids else {}
    for b in pending:
        m = movies.get(b.movie_id)
        b.movie_title = m.title if m else f"Movie #{b.movie_id}"
    return render(request, 'movieflex/admin_booking_list.html', {'bookings': pending})


@login_required_mongo
def admin_booking_approve(request, booking_id):
    if not request.user.is_staff:
        raise Http404()
    booking = Booking.objects(booking_id=booking_id).first()
    if not booking:
        raise Http404("Booking not found")
    booking.approval_status = 'Approved'
    booking.save()
    # Send ticket email now
    movie = Movie.objects(movie_id=booking.movie_id).first()
    qr_data = f"BookingID:{booking.booking_id}, Movie:{movie.title if movie else ''}, Showtime:{booking.showtime}, Seats:{', '.join(booking.seats_list)}"
    qr_img = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    recipient_user = User.objects.filter(id=booking.user_id).first()
    recipient_email = recipient_user.email if recipient_user and recipient_user.email else None
    if recipient_email:
        subject = f"Your Movie Ticket - Booking #{booking.booking_id}"
        body = (
            f"Hello {recipient_user.username if recipient_user else ''},\n\n"
            f"Your booking has been approved. Details:\n"
            f"Booking ID: {booking.booking_id}\n"
            f"Movie: {movie.title if movie else ''}\n"
            f"Showtime: {booking.showtime}\n"
            f"Seats: {', '.join(booking.seats_list)}\n\n"
            f"Your QR ticket is attached.\n"
        )
        email = EmailMessage(subject, body, to=[recipient_email])
        email.attach(filename=f"ticket_{booking.booking_id}.png", content=buffer.getvalue(), mimetype="image/png")
        email.send(fail_silently=True)
    messages.success(request, "Booking approved and ticket emailed.")
    return redirect('admin_booking_queue')


@login_required_mongo
def admin_booking_reject(request, booking_id):
    if not request.user.is_staff:
        raise Http404()
    booking = Booking.objects(booking_id=booking_id).first()
    if not booking:
        raise Http404("Booking not found")
    booking.approval_status = 'Rejected'
    booking.save()
    messages.info(request, "Booking rejected.")
    return redirect('admin_booking_queue')

# ---------------- QR Code Ticket ----------------
@login_required_mongo
def ticket_download(request, booking_id):
    booking = Booking.objects(booking_id=booking_id, user_id=request.user.id).first()
    if not booking:
        raise Http404("Booking not found")
    movie = Movie.objects(movie_id=booking.movie_id).first()
    if not movie:
        raise Http404("Movie not found")

    qr_data = f"BookingID:{booking.booking_id}, Movie:{movie.title}, Showtime:{booking.showtime}, Seats:{', '.join(booking.seats_list)}"
    qr = qrcode.make(qr_data)

    response = HttpResponse(content_type="image/png")
    qr.save(response, "PNG")
    return response
