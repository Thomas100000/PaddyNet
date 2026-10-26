import re
from django.db import models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import role_required
from farms.models import FarmerProfile, Field
from millowner.models import MillOwnerProfile
from billing.models import Bill
from notices.models import Notification
from .forms import BillForm, NotificationForm

def generate_farmer_id():
    """
    Generates a unique autoincrement farmer ID starting with 'PDN' followed by numbers.
    Starts at PDN1001.
    """
    existing_profiles = FarmerProfile.objects.filter(farmer_id__isnull=False).exclude(farmer_id='')
    max_num = 1000

    for profile in existing_profiles:
        if profile.farmer_id and profile.farmer_id.startswith('PDN'):
            num_part = profile.farmer_id[3:]
            digits = re.findall(r'\d+', num_part)
            if digits:
                num = int(digits[0])
                if num > max_num:
                    max_num = num

    next_num = max_num + 1
    new_id = f"PDN{next_num}"

    while FarmerProfile.objects.filter(farmer_id=new_id).exists():
        next_num += 1
        new_id = f"PDN{next_num}"

    return new_id


@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    """
    Admin dashboard featuring:
    - Counts of total farmers, total mill owners, and pending bills.
    - Recent Notifications widget.
    - Pending verification approvals for farmers and mill owners.
    """
    total_farmers = FarmerProfile.objects.count()
    total_millowners = MillOwnerProfile.objects.count()
    pending_bills_count = Bill.objects.filter(status=Bill.Status.PENDING).count()
    recent_notifications = Notification.objects.select_related('posted_by').order_by('-created_at')[:6]

    pending_farmers = FarmerProfile.objects.filter(is_verified=False).select_related('user')
    verified_farmers = FarmerProfile.objects.filter(is_verified=True).select_related('user')
    pending_millowners = MillOwnerProfile.objects.filter(is_verified=False).select_related('user')
    verified_millowners = MillOwnerProfile.objects.filter(is_verified=True).select_related('user')

    context = {
        'total_farmers': total_farmers,
        'total_millowners': total_millowners,
        'pending_bills_count': pending_bills_count,
        'recent_notifications': recent_notifications,
        'pending_farmers': pending_farmers,
        'verified_farmers': verified_farmers,
        'pending_millowners': pending_millowners,
        'verified_millowners': verified_millowners,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
@role_required('ADMIN')
def farmer_list_view(request):
    """
    Farmer list page:
    Table of all FarmerProfile records with name, village, phone,
    and a link to each farmer's detail page.
    """
    search_query = request.GET.get('q', '').strip()
    farmers = FarmerProfile.objects.select_related('user').order_by('-id')

    if search_query:
        query = Q(full_name__icontains=search_query)
        query.add(Q(village__icontains=search_query), Q.OR)
        query.add(Q(phone_number__icontains=search_query), Q.OR)
        query.add(Q(farmer_id__icontains=search_query), Q.OR)
        query.add(Q(user__username__icontains=search_query), Q.OR)
        farmers = farmers.filter(query)

    return render(request, 'admin_panel/farmer_list.html', {
        'farmers': farmers,
        'search_query': search_query,
        'total_count': farmers.count(),
    })


@login_required
@role_required('ADMIN')
def farmer_detail_view(request, farmer_id):
    """
    Farmer detail page:
    Shows farmer profile info and a read-only list of their Field entries
    (reusing Field model from farms app).
    """
    farmer = get_object_or_404(FarmerProfile.objects.select_related('user'), id=farmer_id)
    fields = Field.objects.filter(owner=farmer.user).prefetch_related('activities').order_by('-created_at')

    # Calculate aggregate stats for the farmer's fields
    total_fields = fields.count()
    total_acres = sum([f.extent_area for f in fields]) if total_fields else 0
    total_yield = sum([f.total_harvest_yield for f in fields]) if total_fields else 0

    return render(request, 'admin_panel/farmer_detail.html', {
        'farmer': farmer,
        'fields': fields,
        'total_fields': total_fields,
        'total_acres': total_acres,
        'total_yield': total_yield,
    })


@login_required
@role_required('ADMIN')
def bill_management_view(request):
    """
    Bill management page:
    - List of bills filterable by status (ALL, PENDING, PAID, DISPUTED).
    - Add Bill form (select farmer, category dropdown, amount, file upload, optional remarks).
    - Toggle status / resolve dispute action.
    """
    status_filter = request.GET.get('status', '').strip().upper()

    if request.method == 'POST':
        form = BillForm(request.POST, request.FILES)
        if form.is_valid():
            bill = form.save()
            messages.success(
                request,
                f"Bill #{bill.id} ({bill.description}) for {bill.farmer.username} (₹{bill.amount}) has been created successfully."
            )
            return redirect('admin_bills')
    else:
        form = BillForm()

    bills_queryset = Bill.objects.select_related('farmer', 'farmer__farmer_profile').order_by('-date_issued', '-id')

    if status_filter in [Bill.Status.PENDING, Bill.Status.PAID, Bill.Status.DISPUTED]:
        bills = bills_queryset.filter(status=status_filter)
    else:
        bills = bills_queryset

    # Metrics
    total_count = bills_queryset.count()
    pending_count = bills_queryset.filter(status=Bill.Status.PENDING).count()
    paid_count = bills_queryset.filter(status=Bill.Status.PAID).count()
    disputed_count = bills_queryset.filter(status=Bill.Status.DISPUTED).count()

    return render(request, 'admin_panel/bills.html', {
        'form': form,
        'bills': bills,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'paid_count': paid_count,
        'disputed_count': disputed_count,
    })


@login_required
@role_required('ADMIN')
def toggle_bill_status_view(request, bill_id):
    """
    Toggles the bill status between PENDING, PAID, or resolves DISPUTED.
    """
    bill = get_object_or_404(Bill, id=bill_id)
    if bill.status in [Bill.Status.PENDING, Bill.Status.DISPUTED]:
        bill.status = Bill.Status.PAID
    else:
        bill.status = Bill.Status.PENDING
    bill.save()

    messages.success(
        request,
        f"Bill #{bill.id} status updated to {bill.get_status_display()}."
    )
    return redirect('admin_bills')



@login_required
@role_required('ADMIN')
def post_notification_view(request):
    """
    Post Notification form view:
    Title + message, saved with posted_by=request.user.
    """
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.posted_by = request.user
            notification.save()
            messages.success(request, f"Notification '{notification.title}' has been broadcast successfully!")
            return redirect('admin_dashboard')
    else:
        form = NotificationForm()

    recent_notifications = Notification.objects.select_related('posted_by').order_by('-created_at')[:8]

    return render(request, 'admin_panel/post_notification.html', {
        'form': form,
        'recent_notifications': recent_notifications,
    })


@login_required
@role_required('ADMIN')
def verify_farmer_view(request, farmer_id):
    farmer = get_object_or_404(FarmerProfile, id=farmer_id)
    farmer.is_verified = True
    if not farmer.farmer_id:
        farmer.farmer_id = generate_farmer_id()
    farmer.save()
    farmer_name = farmer.full_name if farmer.full_name else farmer.user.username
    messages.success(request, f"Farmer '{farmer_name}' has been verified successfully with ID '{farmer.farmer_id}'!")
    return redirect('admin_dashboard')


@login_required
@role_required('ADMIN')
def reject_farmer_view(request, farmer_id):
    farmer = get_object_or_404(FarmerProfile, id=farmer_id)
    farmer_name = farmer.full_name if farmer.full_name else farmer.user.username
    user = farmer.user
    user.delete()
    messages.warning(request, f"Registration for farmer '{farmer_name}' has been rejected.")
    return redirect('admin_dashboard')


@login_required
@role_required('ADMIN')
def verify_millowner_view(request, millowner_id):
    millowner = get_object_or_404(MillOwnerProfile, id=millowner_id)
    millowner.is_verified = True
    millowner.save()
    mill_name = millowner.mill_name if millowner.mill_name else millowner.user.username
    messages.success(request, f"Mill Owner '{mill_name}' (FSSAI: {millowner.fssai_license_number}) has been verified successfully!")
    return redirect('admin_dashboard')


@login_required
@role_required('ADMIN')
def reject_millowner_view(request, millowner_id):
    millowner = get_object_or_404(MillOwnerProfile, id=millowner_id)
    mill_name = millowner.mill_name if millowner.mill_name else millowner.user.username
    user = millowner.user
    user.delete()
    messages.warning(request, f"Registration for Mill Owner '{mill_name}' has been rejected.")
    return redirect('admin_dashboard')
