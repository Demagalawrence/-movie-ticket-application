from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Movie, Booking

# -----------------------------
# User Registrations Form (SQLite)
# -----------------------------
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


# -----------------------------
# User Login Form
# -----------------------------
class UserLoginForm(forms.Form):
    user = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Username or Email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password"
    )


# -----------------------------
# Movie Form (MongoDB, Admin Only)
# -----------------------------
class MovieForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    type = forms.CharField(
        max_length=50,
        label="Genre/Type",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    duration = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    showtimes = forms.CharField(
        help_text="Enter showtimes separated by commas, e.g., 13:00,17:00",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    poster = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )


# -----------------------------
# Booking Form (MongoDB)
# -----------------------------
class BookingForm(forms.Form):
    showtime = forms.ChoiceField(
        choices=[],  # Will be populated dynamically in the view
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    seats = forms.CharField(
        help_text="Enter seat codes separated by commas, e.g., A1,A2",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_seats(self):
        seats = self.cleaned_data.get('seats', '')
        seats_list = [s.strip().upper() for s in seats.split(',') if s.strip()]
        if not seats_list:
            raise ValidationError("You must enter at least one seat.")
        return seats_list
