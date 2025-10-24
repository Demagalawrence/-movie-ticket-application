from mongoengine import Document, StringField, IntField, ListField, DictField

# -----------------------------
# Movies Collection
# -----------------------------
class Movie(Document):
    movie_id = IntField(required=True, unique=True)  # optional: auto-generate in code
    title = StringField(required=True, max_length=200)
    type = StringField(required=True)          # e.g., "Action", "Comedy"
    duration = IntField() 
    poster = StringField()                         # in minutes
    showtimes = ListField(StringField())        # e.g., ["13:00", "17:00"]
    available_seats = DictField()               # { '13:00': 30, '17:00': 30 }
    booked_seats = DictField(default=dict)      # { '13:00': ['A1','A2'] }

    meta = {
        'collection': 'movies'
    }

    def __str__(self):
        return self.title


# -----------------------------
# Bookings Collection
# -----------------------------
class Booking(Document):
    booking_id = IntField(required=True, unique=True)  # unique booking number
    user_id = IntField(required=True)                  # links to SQLite User.id
    movie_id = IntField(required=True)                 # links to Movie.movie_id
    seats_list = ListField(StringField())               # e.g., ['A1','A2']
    seats_booked = IntField(default=0)             
    showtime = StringField()
    payment_status = StringField(choices=['Pending','Paid','Cancelled'], default='Pending')
    approval_status = StringField(choices=['Pending','Approved','Rejected'], default='Pending')

    meta = {'collection': 'bookings'}
