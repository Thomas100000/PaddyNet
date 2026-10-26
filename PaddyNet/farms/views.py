import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone

from accounts.decorators import role_required
from billing.models import Bill
from notices.models import Notification
from .models import Field, FarmingActivity
from .forms import FieldForm, FarmingActivityForm


@login_required
@role_required('FARMER')
def farmer_dashboard(request):
    profile = getattr(request.user, 'farmer_profile', None)
    fields = Field.objects.filter(owner=request.user).annotate(
        activity_count=Count('activities')
    ).order_by('-created_at')

    total_fields = fields.count()
    total_acres = fields.aggregate(total=Sum('extent_area'))['total'] or 0
    total_harvest = FarmingActivity.objects.filter(
        field__owner=request.user,
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).aggregate(total=Sum('yield_kg'))['total'] or 0

    recent_activities = FarmingActivity.objects.filter(
        field__owner=request.user
    ).select_related('field').order_by('-activity_date', '-created_at')[:5]

    # Bills, Bids & Notices overview for farmer
    pending_bills_count = Bill.objects.filter(farmer=request.user, status=Bill.Status.PENDING).count()
    total_bills_count = Bill.objects.filter(farmer=request.user).count()
    recent_notifications = Notification.objects.select_related('posted_by').order_by('-created_at')[:3]
    
    from millowner.models import Bid
    total_bids_received = Bid.objects.filter(field__owner=request.user).count()

    return render(request, 'farms/dashboard.html', {
        'profile': profile,
        'fields': fields[:4],
        'total_fields': total_fields,
        'total_acres': total_acres,
        'total_harvest': total_harvest,
        'recent_activities': recent_activities,
        'pending_bills_count': pending_bills_count,
        'total_bills_count': total_bills_count,
        'recent_notifications': recent_notifications,
        'total_bids_received': total_bids_received,
    })


@login_required
@role_required('FARMER')
def field_list(request):
    fields = Field.objects.filter(owner=request.user).annotate(
        activity_count=Count('activities'),
        harvest_yield=Sum('activities__yield_kg', filter=Q(activities__activity_type=FarmingActivity.ActivityType.HARVEST))
    ).order_by('-created_at')

    total_fields = fields.count()
    total_acres = fields.aggregate(total=Sum('extent_area'))['total'] or 0

    return render(request, 'farms/field_list.html', {
        'fields': fields,
        'total_fields': total_fields,
        'total_acres': total_acres,
    })


@login_required
@role_required('FARMER')
def field_create(request):
    if request.method == 'POST':
        form = FieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.owner = request.user
            field.save()
            messages.success(request, f"Field '{field.field_name}' added successfully!")
            return redirect('field_detail', field_id=field.id)
    else:
        form = FieldForm()

    return render(request, 'farms/field_form.html', {
        'form': form,
        'is_edit': False,
        'title': 'Add New Paddy Field',
    })


@login_required
@role_required('FARMER')
def field_edit(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)

    if request.method == 'POST':
        form = FieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, f"Field '{field.field_name}' updated successfully.")
            return redirect('field_detail', field_id=field.id)
    else:
        form = FieldForm(instance=field)

    return render(request, 'farms/field_form.html', {
        'form': form,
        'field': field,
        'is_edit': True,
        'title': f"Edit Field: {field.field_name}",
    })


@login_required
@role_required('FARMER')
def field_delete(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)

    if request.method == 'POST':
        name = field.field_name
        field.delete()
        messages.success(request, f"Field '{name}' and its activity history have been deleted.")
        return redirect('field_list')

    return render(request, 'farms/field_confirm_delete.html', {
        'field': field,
    })


@login_required
@role_required('FARMER')
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)

    if request.method == 'POST':
        activity_form = FarmingActivityForm(request.POST)
        if activity_form.is_valid():
            activity = activity_form.save(commit=False)
            activity.field = field
            activity.save()
            messages.success(request, f"Logged {activity.get_activity_type_display()} successfully!")
            return redirect('field_detail', field_id=field.id)
    else:
        activity_form = FarmingActivityForm(initial={
            'activity_date': timezone.now().date(),
        })

    activities = field.activities.all().order_by('activity_date', 'created_at')
    total_activities = activities.count()
    harvest_yield = activities.filter(
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).aggregate(total=Sum('yield_kg'))['total'] or 0

    return render(request, 'farms/field_detail.html', {
        'field': field,
        'activities': activities,
        'activity_form': activity_form,
        'total_activities': total_activities,
        'harvest_yield': harvest_yield,
    })


@login_required
@role_required('FARMER')
def activity_delete(request, activity_id):
    activity = get_object_or_404(FarmingActivity, id=activity_id, field__owner=request.user)
    field_id = activity.field.id

    if request.method == 'POST':
        activity_name = activity.get_activity_type_display()
        activity.delete()
        messages.success(request, f"Activity record '{activity_name}' was removed.")

    return redirect('field_detail', field_id=field_id)


@login_required
@role_required('FARMER')
def field_statistics(request, field_id=None):
    farmer_fields = Field.objects.filter(owner=request.user).order_by('field_name')

    selected_field = None
    if field_id:
        selected_field = get_object_or_404(Field, id=field_id, owner=request.user)
    else:
        req_field_id = request.GET.get('field')
        if req_field_id:
            selected_field = get_object_or_404(Field, id=req_field_id, owner=request.user)
        else:
            selected_field = farmer_fields.first()

    season_data = []
    chart_labels = []
    chart_yields = []
    total_yield_all = 0
    highest_season_yield = 0

    if selected_field:
        # Group activities by season_year
        raw_stats = (
            selected_field.activities
            .values('season_year')
            .annotate(
                total_yield=Sum('yield_kg', filter=Q(activity_type=FarmingActivity.ActivityType.HARVEST)),
                activity_count=Count('id'),
                harvest_count=Count('id', filter=Q(activity_type=FarmingActivity.ActivityType.HARVEST))
            )
            .order_by('season_year')
        )

        for item in raw_stats:
            season = item['season_year']
            y_kg = float(item['total_yield'] or 0)
            act_count = item['activity_count']
            harv_count = item['harvest_count']
            per_acre = round(y_kg / float(selected_field.extent_area), 2) if selected_field.extent_area > 0 else 0

            season_data.append({
                'season_year': season,
                'total_yield': y_kg,
                'yield_per_acre': per_acre,
                'activity_count': act_count,
                'harvest_count': harv_count,
            })

            chart_labels.append(season)
            chart_yields.append(y_kg)

            total_yield_all += y_kg
            if y_kg > highest_season_yield:
                highest_season_yield = y_kg

    return render(request, 'farms/field_statistics.html', {
        'farmer_fields': farmer_fields,
        'selected_field': selected_field,
        'season_data': season_data,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_yields_json': json.dumps(chart_yields),
        'total_yield_all': total_yield_all,
        'highest_season_yield': highest_season_yield,
    })


@login_required
@role_required('FARMER')
def farmer_notifications(request):
    """
    Farmer Notifications page:
    Lists all Notification entries, newest first.
    """
    notifications = Notification.objects.select_related('posted_by').order_by('-created_at', '-id')
    return render(request, 'farms/notifications.html', {
        'notifications': notifications,
        'total_count': notifications.count(),
    })


import uuid

@login_required
@role_required('FARMER')
def farmer_bills(request):
    """
    Farmer "My Bills" page:
    Shows the logged-in farmer's own Bill entries and their payment status.
    Filterable by status (ALL, PENDING, PAID, DISPUTED).
    Allows paying bills via dummy payment gateway, viewing bills, and raising disputes.
    """
    status_filter = request.GET.get('status', '').strip().upper()
    bills_queryset = Bill.objects.filter(farmer=request.user).order_by('-date_issued', '-id')

    if status_filter in [Bill.Status.PENDING, Bill.Status.PAID, Bill.Status.DISPUTED]:
        bills = bills_queryset.filter(status=status_filter)
    else:
        bills = bills_queryset

    total_count = bills_queryset.count()
    pending_count = bills_queryset.filter(status=Bill.Status.PENDING).count()
    paid_count = bills_queryset.filter(status=Bill.Status.PAID).count()
    disputed_count = bills_queryset.filter(status=Bill.Status.DISPUTED).count()

    total_amount = bills_queryset.aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = bills_queryset.filter(status=Bill.Status.PENDING).aggregate(total=Sum('amount'))['total'] or 0
    paid_amount = bills_queryset.filter(status=Bill.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0
    disputed_amount = bills_queryset.filter(status=Bill.Status.DISPUTED).aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'farms/bills.html', {
        'bills': bills,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'paid_count': paid_count,
        'disputed_count': disputed_count,
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
        'disputed_amount': disputed_amount,
    })


@login_required
@role_required('FARMER')
def farmer_pay_bill(request, bill_id):
    """
    Dummy payment gateway view for paying community bills.
    Supports GET (standalone payment portal page) and POST (processes simulated payment).
    """
    bill = get_object_or_404(Bill, id=bill_id, farmer=request.user)

    if bill.status == Bill.Status.PAID:
        messages.info(request, f"Bill #{bill.id} has already been settled and paid.")
        return redirect('farmer_bills')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'UPI (Instant)').strip()
        txn_ref = f"TXN-PDN-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"

        bill.status = Bill.Status.PAID
        bill.payment_method = payment_method
        bill.transaction_id = txn_ref
        bill.paid_at = timezone.now()
        bill.save()

        messages.success(
            request,
            f"Payment of ₹{bill.amount} for Bill #{bill.id} ({bill.description}) was successful! Ref: {txn_ref}."
        )
        return redirect('farmer_bills')

    return render(request, 'farms/pay_bill.html', {
        'bill': bill,
    })


@login_required
@role_required('FARMER')
def farmer_raise_dispute(request, bill_id):
    """
    Allows a farmer to contest or raise a dispute on a bill.
    Sets status to DISPUTED and records the farmer's stated reason.
    """
    bill = get_object_or_404(Bill, id=bill_id, farmer=request.user)

    if request.method == 'POST':
        if bill.status == Bill.Status.DISPUTED:
            messages.info(request, f"A dispute is already under review for Bill #{bill.id}.")
            return redirect('farmer_bills')

        dispute_type = request.POST.get('dispute_type', '').strip()
        dispute_details = request.POST.get('dispute_details', '').strip()

        if not dispute_details and not dispute_type:
            messages.error(request, "Please provide a valid explanation or reason for your dispute.")
            return redirect('farmer_bills')

        if dispute_type and dispute_details:
            reason = f"[{dispute_type}] {dispute_details}"
        else:
            reason = dispute_details or dispute_type

        bill.status = Bill.Status.DISPUTED
        bill.dispute_reason = reason
        bill.disputed_at = timezone.now()
        bill.save()

        messages.success(
            request,
            f"Dispute for Bill #{bill.id} has been submitted to the Admin committee for verification."
        )
        return redirect('farmer_bills')

    return redirect('farmer_bills')



@login_required
@role_required('FARMER')
def farmer_bids(request):
    """
    Farmer "Mill Owner Bids" page:
    Lists all bids placed by mill owners on each of the logged-in farmer's fields.
    Bids are sorted by amount descending per field, showing mill owner name,
    mill details, amount, date, and notes, so the farmer can compare offers easily.
    """
    from millowner.models import Bid

    fields = Field.objects.filter(owner=request.user).prefetch_related(
        'bids', 'bids__millowner', 'bids__millowner__millowner_profile', 'activities'
    ).order_by('-created_at')

    fields_with_bids = []
    total_bids_count = 0
    highest_offer = 0

    for f in fields:
        field_bids = f.bids.all().order_by('-amount', '-date')
        bid_count = field_bids.count()
        total_bids_count += bid_count

        field_highest = field_bids.first().amount if field_bids.exists() else 0
        if field_highest and field_highest > highest_offer:
            highest_offer = field_highest

        latest_harvest = f.activities.filter(
            activity_type=FarmingActivity.ActivityType.HARVEST
        ).order_by('-activity_date').first()

        fields_with_bids.append({
            'field': f,
            'bids': field_bids,
            'bid_count': bid_count,
            'highest_bid': field_highest,
            'latest_harvest': latest_harvest,
        })

    return render(request, 'farms/bids.html', {
        'fields_with_bids': fields_with_bids,
        'total_bids_count': total_bids_count,
        'highest_offer': highest_offer,
        'total_fields_count': fields.count(),
    })


@login_required
@role_required('FARMER')
def farmer_respond_bid(request, bid_id):
    """
    Handle farmer's decision on a mill owner's bid:
    - Accept bid: Sets status to ACCEPTED with optional confirmation note
    - Reject bid: Sets status to REJECTED with optional decline note
    - Bargain: Proposes a counter-offer amount / per kg rate and sends a note to the mill owner
    - Reset: Reverts to PENDING
    """
    from millowner.models import Bid
    bid = get_object_or_404(Bid, id=bid_id)

    # Security check: bid must belong to a field owned by the logged-in farmer
    if bid.field.owner != request.user:
        messages.error(request, "Permission denied. You can only respond to bids on your own fields.")
        return redirect('farmer_bids')

    if request.method == 'POST':
        action = request.POST.get('action')
        farmer_note = request.POST.get('farmer_note', '').strip()
        mill_profile = getattr(bid.millowner, 'millowner_profile', None)
        mill_name = mill_profile.mill_name if mill_profile and mill_profile.mill_name else bid.millowner.username

        if action == 'accept':
            bid.status = Bid.Status.ACCEPTED
            bid.farmer_note = farmer_note
            bid.responded_at = timezone.now()
            bid.save()
            messages.success(request, f"Bid of ₹{bid.amount} from {mill_name} has been accepted successfully! 🎉")

        elif action == 'reject':
            bid.status = Bid.Status.REJECTED
            bid.farmer_note = farmer_note
            bid.responded_at = timezone.now()
            bid.save()
            messages.warning(request, f"Bid of ₹{bid.amount} from {mill_name} has been declined.")

        elif action == 'bargain':
            counter_amount_raw = request.POST.get('counter_amount', '').strip()
            counter_rate_raw = request.POST.get('counter_per_kg_rate', '').strip()

            counter_amount = None
            counter_per_kg_rate = None

            if counter_amount_raw:
                try:
                    counter_amount = float(counter_amount_raw)
                    if counter_amount <= 0:
                        raise ValueError()
                except ValueError:
                    messages.error(request, "Please enter a valid positive counter-offer amount.")
                    return redirect('farmer_bids')

            if counter_rate_raw:
                try:
                    counter_per_kg_rate = float(counter_rate_raw)
                    if counter_per_kg_rate <= 0:
                        raise ValueError()
                except ValueError:
                    messages.error(request, "Please enter a valid positive per-kg rate.")
                    return redirect('farmer_bids')

            if not counter_amount and not counter_per_kg_rate and not farmer_note:
                messages.error(request, "Please enter a counter offer amount, rate, or a bargaining note.")
                return redirect('farmer_bids')

            bid.status = Bid.Status.BARGAINING
            bid.counter_amount = counter_amount
            bid.counter_per_kg_rate = counter_per_kg_rate
            bid.farmer_note = farmer_note
            bid.responded_at = timezone.now()
            bid.save()
            messages.success(request, f"Bargain note and counter-offer sent to {mill_name}! 💬")

        elif action == 'reset':
            bid.status = Bid.Status.PENDING
            bid.counter_amount = None
            bid.counter_per_kg_rate = None
            bid.farmer_note = ''
            bid.responded_at = None
            bid.save()
            messages.info(request, f"Bid status reset to Pending Review.")

    return redirect('farmer_bids')


@login_required
@role_required('FARMER')
def farmer_harvest_yield_pdf(request):
    """
    Generates and downloads a PDF report of the logged-in farmer's
    complete harvest yield history across all their registered fields.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    profile = getattr(request.user, 'farmer_profile', None)
    farmer_name = (profile.full_name if profile and profile.full_name else request.user.username)
    farmer_id_str = (profile.farmer_id if profile and profile.farmer_id else 'N/A')
    village = (profile.village if profile and profile.village else 'N/A')

    fields = Field.objects.filter(owner=request.user).order_by('field_name')
    all_harvest_activities = FarmingActivity.objects.filter(
        field__owner=request.user,
        activity_type=FarmingActivity.ActivityType.HARVEST,
    ).select_related('field').order_by('field__field_name', '-activity_date')

    grand_total_yield = all_harvest_activities.aggregate(total=Sum('yield_kg'))['total'] or 0

    # Build per-field data dict
    field_harvests = {}
    for fa in all_harvest_activities:
        fid = fa.field_id
        if fid not in field_harvests:
            field_harvests[fid] = {'field': fa.field, 'activities': []}
        field_harvests[fid]['activities'].append(fa)

    # --- PDF Setup ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    GREEN_DARK  = colors.HexColor('#1b4332')
    ACCENT      = colors.HexColor('#40916c')
    GREEN_PALE  = colors.HexColor('#f0fdf4')
    GREEN_BORDER = colors.HexColor('#bbf7d0')
    MUTED       = colors.HexColor('#6b7280')
    WHITE       = colors.white
    HARVEST_GREEN = colors.HexColor('#15803d')

    styles = getSampleStyleSheet()
    section_header_style = ParagraphStyle('SH', parent=styles['Normal'],
        fontSize=11, textColor=GREEN_DARK, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=5)
    normal_style = ParagraphStyle('N', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#374151'), leading=14)
    muted_style = ParagraphStyle('M', parent=styles['Normal'],
        fontSize=8, textColor=MUTED, leading=12)
    bold_style = ParagraphStyle('B', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold', textColor=GREEN_DARK)

    story = []

    # --- Header Banner ---
    header_data = [[
        Paragraph('PaddyNet', ParagraphStyle('H', parent=styles['Normal'],
            fontSize=22, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_LEFT)),
        Paragraph('Harvest Yield History Report', ParagraphStyle('HR', parent=styles['Normal'],
            fontSize=12, fontName='Helvetica-Bold', textColor=colors.HexColor('#d8f3dc'), alignment=TA_RIGHT))
    ]]
    ht = Table(header_data, colWidths=[9*cm, 8*cm])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GREEN_DARK),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (0,-1), 16),
        ('RIGHTPADDING', (-1,0), (-1,-1), 16),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.4*cm))

    now_str = timezone.localtime(timezone.now()).strftime('%d %B %Y, %I:%M %p')
    story.append(Paragraph(f'Generated: {now_str}',
        ParagraphStyle('Gen', parent=styles['Normal'], fontSize=8, textColor=MUTED, alignment=TA_RIGHT)))
    story.append(Spacer(1, 0.35*cm))

    # --- Farmer Info Box ---
    farmer_data = [
        [Paragraph('<b>Farmer Name</b>', bold_style), Paragraph(farmer_name, normal_style),
         Paragraph('<b>Farmer ID</b>', bold_style), Paragraph(farmer_id_str, normal_style)],
        [Paragraph('<b>Village</b>', bold_style), Paragraph(village, normal_style),
         Paragraph('<b>Total Fields</b>', bold_style), Paragraph(str(fields.count()), normal_style)],
    ]
    ft = Table(farmer_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 4.5*cm])
    ft.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GREEN_PALE),
        ('GRID', (0,0), (-1,-1), 0.5, GREEN_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(ft)
    story.append(Spacer(1, 0.4*cm))

    # --- Grand Total Banner ---
    gt_data = [[
        Paragraph('Grand Total Harvest Yield — All Fields & Seasons', ParagraphStyle('GT', parent=styles['Normal'],
            fontSize=11, fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph(f'{float(grand_total_yield):,.0f} kg', ParagraphStyle('GTV', parent=styles['Normal'],
            fontSize=17, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT))
    ]]
    gtt = Table(gt_data, colWidths=[12*cm, 5*cm])
    gtt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (0,-1), 14),
        ('RIGHTPADDING', (-1,0), (-1,-1), 14),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(gtt)
    story.append(Spacer(1, 0.6*cm))

    # --- Per-Field Harvest Sections ---
    if field_harvests:
        for fid, fdata in field_harvests.items():
            f = fdata['field']
            activities = fdata['activities']
            field_total = sum((float(a.yield_kg) for a in activities if a.yield_kg), 0)

            # Field sub-header
            story.append(Paragraph(
                f'🌾  {f.field_name}  —  {f.location}  ({f.extent_area} Acres)',
                section_header_style))
            story.append(HRFlowable(width='100%', thickness=1, color=ACCENT, spaceAfter=5))

            # Table
            col_headers = ['#', 'Harvest Date', 'Season / Year', 'Yield (kg)', 'kg / Acre', 'Notes']
            tdata = [[Paragraph(f'<b>{h}</b>',
                ParagraphStyle('TH', parent=styles['Normal'], fontSize=8,
                    fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER))
                for h in col_headers]]

            for idx, ha in enumerate(activities, 1):
                yv = float(ha.yield_kg) if ha.yield_kg else None
                ys = f'{yv:,.0f}' if yv else 'Pending'
                pa = f'{yv / float(f.extent_area):,.1f}' if (yv and f.extent_area > 0) else '—'
                tdata.append([
                    Paragraph(str(idx), muted_style),
                    Paragraph(ha.activity_date.strftime('%d %b %Y'), normal_style),
                    Paragraph(ha.season_year or '—', normal_style),
                    Paragraph(f'<b>{ys} kg</b>',
                        ParagraphStyle('YV', parent=styles['Normal'], fontSize=9,
                            fontName='Helvetica-Bold', textColor=HARVEST_GREEN)),
                    Paragraph(pa, muted_style),
                    Paragraph(ha.notes[:100] + ('…' if ha.notes and len(ha.notes) > 100 else '') if ha.notes else '—',
                        muted_style),
                ])

            # Field total row
            tdata.append([
                Paragraph('', muted_style),
                Paragraph('', muted_style),
                Paragraph('<b>Field Total</b>',
                    ParagraphStyle('FT', parent=styles['Normal'], fontSize=9,
                        fontName='Helvetica-Bold', textColor=GREEN_DARK, alignment=TA_RIGHT)),
                Paragraph(f'<b>{field_total:,.0f} kg</b>',
                    ParagraphStyle('FTV', parent=styles['Normal'], fontSize=10,
                        fontName='Helvetica-Bold', textColor=HARVEST_GREEN)),
                Paragraph('', muted_style),
                Paragraph('', muted_style),
            ])

            htable = Table(tdata, colWidths=[0.8*cm, 2.8*cm, 3.2*cm, 2.6*cm, 2.4*cm, 5.2*cm])
            htable.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), GREEN_DARK),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, GREEN_PALE]),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#dcfce7')),
                ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#d1fae5')),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (0,-1), 'CENTER'),
                ('ALIGN', (3,0), (4,-1), 'RIGHT'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            story.append(htable)
            story.append(Spacer(1, 0.5*cm))
    else:
        story.append(Paragraph('No harvest activities have been recorded yet.', muted_style))

    # --- Footer ---
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#d1d5db'), spaceAfter=5))
    story.append(Paragraph(
        'This report is auto-generated by PaddyNet — Agricultural Produce Management Platform. '
        'All data reflects recorded activities as of the report generation timestamp.',
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7.5, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    filename = f'HarvestYieldReport_{request.user.username}.pdf'
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
