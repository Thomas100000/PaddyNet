from django import forms
from .models import Field, FarmingActivity

class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['field_name', 'location', 'extent_area', 'field_identifier']
        widgets = {
            'field_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. North Polder, Block 4, Kayal Plot'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Kainakary Ward 3, Padasekharam A'
            }),
            'extent_area': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Extent in acres (e.g. 2.50)',
                'step': '0.01',
                'min': '0.01'
            }),
            'field_identifier': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Survey No. or Code (e.g. SY-104/2)'
            }),
        }

    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Kainakary Ward 3, Padasekharam A'
        }),
        label="Location"
    )

    extent_area = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=0.01,
        error_messages={
            'required': 'Please enter the field extent in acres.',
            'min_value': 'Extent area must be greater than zero acres.',
            'invalid': 'Please enter a valid number of acres.'
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Extent in acres (e.g. 2.50)',
            'step': '0.01',
            'min': '0.01'
        }),
        label="Extent Area (Acres)"
    )

    field_identifier = forms.CharField(
        max_length=50,
        required=True,
        error_messages={
            'required': 'Please enter the Field Code / Survey Number.',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Survey No. or Code (e.g. SY-104/2)'
        }),
        label="Field Code / Survey No."
    )

    def clean_location(self):
        loc = self.cleaned_data.get('location')
        if not loc or not loc.strip():
            return 'Kainakary'
        return loc.strip()

    def clean_extent_area(self):
        extent = self.cleaned_data.get('extent_area')
        if extent is not None and extent <= 0:
            raise forms.ValidationError("Extent area must be greater than zero acres.")
        return extent

    def clean_field_identifier(self):
        val = self.cleaned_data.get('field_identifier')
        if not val or not val.strip():
            raise forms.ValidationError("Please enter the Field Code / Survey Number.")
        return val.strip()


class FarmingActivityForm(forms.ModelForm):
    class Meta:
        model = FarmingActivity
        fields = ['activity_type', 'activity_date', 'season_year', 'yield_kg', 'notes']
        widgets = {
            'activity_type': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_activity_type'
            }),
            'activity_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'season_year': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 2025 Kharif, 2025 Rabi, 2024-25 Mundakan',
                'list': 'season_list'
            }),
            'yield_kg': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Harvest yield in kg (e.g. 3200)',
                'step': '0.01',
                'min': '0',
                'id': 'id_yield_kg'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Details on seeds used, fertilizer/pesticide dosage, water level, notes...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        activity_type = cleaned_data.get('activity_type')
        activity_date = cleaned_data.get('activity_date')
        yield_kg = cleaned_data.get('yield_kg')

        if activity_type == FarmingActivity.ActivityType.HARVEST:
            from datetime import date
            # Yield is only required when the harvest date is today or has already passed
            harvest_is_past = activity_date is not None and activity_date <= date.today()
            if harvest_is_past:
                if yield_kg is None:
                    self.add_error(
                        'yield_kg',
                        "Harvest yield in kg is required since the harvest date has already passed."
                    )
                elif yield_kg <= 0:
                    self.add_error(
                        'yield_kg',
                        "Harvest yield must be greater than zero kg."
                    )
            else:
                # Future harvest — yield is optional, but if provided must be positive
                if yield_kg is not None and yield_kg <= 0:
                    self.add_error(
                        'yield_kg',
                        "Harvest yield must be greater than zero kg."
                    )
        else:
            if yield_kg is not None and yield_kg < 0:
                self.add_error('yield_kg', "Yield cannot be negative.")

        return cleaned_data
