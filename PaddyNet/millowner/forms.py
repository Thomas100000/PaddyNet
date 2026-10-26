from django import forms
from .models import Bid

class BidForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        error_messages={
            'required': 'Please enter your bid offer amount.',
            'min_value': 'Bid offer amount must be greater than zero.',
            'invalid': 'Please enter a valid bid amount.'
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Enter offer rate per kg in ₹ (e.g. 28.50)',
            'required': True,
        }),
        label="Offer Amount/kg (₹)"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Optional notes or terms (e.g. Pickup timeline, moisture tolerance, packaging requirements)...'
        }),
        label="Additional Terms / Notes (Optional)"
    )

    def __init__(self, *args, harvest_kg=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.harvest_kg = harvest_kg
        if harvest_kg and harvest_kg > 0:
            self.fields['amount'].label = "Offer Amount/kg (₹)"
            self.fields['amount'].widget.attrs['placeholder'] = "Enter offer rate per kg in ₹ (e.g. 28.50)"
            self.fields['amount'].help_text = f"Rate per kg will be multiplied by {harvest_kg:g} kg to calculate total offer amount."
        else:
            self.fields['amount'].label = "Offer Amount (₹)"
            self.fields['amount'].widget.attrs['placeholder'] = "Enter total bid offer in ₹ (e.g. 50000.00)"
            self.fields['amount'].help_text = "Harvest yield not specified. Enter total purchase offer for parcel."

    class Meta:
        model = Bid
        fields = ['amount', 'notes']

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Bid offer amount must be greater than zero.")
        return amount
