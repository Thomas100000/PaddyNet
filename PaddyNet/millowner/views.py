import io
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Max, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from accounts.decorators import role_required
from farms.models import Field, FarmingActivity, FarmerProfile
from .models import Bid, MillOwnerProfile
from .forms import BidForm

@login_required
@role_required('MILLOWNER')
def millowner_dashboard(request):
    """
    Mill owner dashboard featuring:
    - Quick stats (total bids placed, total bid value, available produce lots).
    - Recent bids placed by this mill owner.
    - Available harvest lots ready for direct procurement.
    """
    profile = getattr(request.user, 'millowner_profile', None)
    my_bids = Bid.objects.filter(millowner=request.user).select_related('field', 'field__owner').order_by('-date')
    
    total_bids_count = my_bids.count()
    total_bid_value = my_bids.aggregate(total=Sum('amount'))['total'] or 0

    # Fields that have at least one HARVEST entry
    harvested_fields = Field.objects.filter(
        activities__activity_type=FarmingActivity.ActivityType.HARVEST
    ).distinct().select_related('owner', 'owner__farmer_profile')
    
    available_harvest_count = harvested_fields.count()
    
    total_harvest_kg = FarmingActivity.objects.filter(
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).aggregate(total=Sum('yield_kg'))['total'] or 0

    # Featured harvest lots ready for bidding
    featured_lots = []
    for field in harvested_fields[:6]:
        latest_harvest = field.activities.filter(
            activity_type=FarmingActivity.ActivityType.HARVEST
        ).order_by('-activity_date').first()
        
        highest_bid = field.bids.aggregate(max_val=Max('amount'))['max_val']
        my_highest_bid = field.bids.filter(millowner=request.user).aggregate(max_val=Max('amount'))['max_val']
        
        featured_lots.append({
            'field': field,
            'latest_harvest': latest_harvest,
            'highest_bid': highest_bid,
            'my_highest_bid': my_highest_bid,
            'total_bids': field.bids.count()
        })

    return render(request, 'millowner/dashboard.html', {
        'profile': profile,
        'total_bids_count': total_bids_count,
        'total_bid_value': total_bid_value,
        'available_harvest_count': available_harvest_count,
        'total_harvest_kg': total_harvest_kg,
        'recent_bids': my_bids[:5],
        'featured_lots': featured_lots,
    })


@login_required
@role_required('MILLOWNER')
def millowner_field_browse(request):
    """
    Farmer & harvest lot browse page:
    Lists fields that have at least one HARVEST-type FarmingActivity entry ("available produce").
    Displays field location, extent area, latest harvest yield_kg, and current bidding status.
    """
    search_query = request.GET.get('q', '').strip()
    
    harvested_fields_qs = Field.objects.filter(
        activities__activity_type=FarmingActivity.ActivityType.HARVEST
    ).distinct().select_related('owner', 'owner__farmer_profile').order_by('-created_at')

    if search_query:
        query = Q(field_name__icontains=search_query)
        query.add(Q(location__icontains=search_query), Q.OR)
        query.add(Q(owner__username__icontains=search_query), Q.OR)
        query.add(Q(owner__first_name__icontains=search_query), Q.OR)
        if hasattr(Field, 'owner') and hasattr(FarmerProfile, 'full_name'):
            query.add(Q(owner__farmer_profile__full_name__icontains=search_query), Q.OR)
            query.add(Q(owner__farmer_profile__village__icontains=search_query), Q.OR)
        harvested_fields_qs = harvested_fields_qs.filter(query)

    fields_data = []
    for field in harvested_fields_qs:
        harvest_activities = field.activities.filter(
            activity_type=FarmingActivity.ActivityType.HARVEST
        ).order_by('-activity_date')
        
        latest_harvest = harvest_activities.first()
        total_field_yield = harvest_activities.aggregate(tot=Sum('yield_kg'))['tot'] or 0
        
        highest_bid = field.bids.aggregate(max_bid=Max('amount'))['max_bid']
        my_bids_on_field = field.bids.filter(millowner=request.user).order_by('-date')
        
        fields_data.append({
            'field': field,
            'latest_harvest': latest_harvest,
            'total_field_yield': total_field_yield,
            'highest_bid': highest_bid,
            'bid_count': field.bids.count(),
            'my_bids_count': my_bids_on_field.count(),
            'my_latest_bid': my_bids_on_field.first(),
        })

    return render(request, 'millowner/field_browse.html', {
        'fields_data': fields_data,
        'search_query': search_query,
        'total_count': len(fields_data),
    })


@login_required
@role_required('MILLOWNER')
def millowner_field_detail(request, field_id):
    """
    Field detail page (Mill Owner View):
    Shows field specifications, harvest activity history, and a 'Place Bid' form.
    """
    field = get_object_or_404(
        Field.objects.select_related('owner', 'owner__farmer_profile'),
        id=field_id
    )
    
    harvest_activities = field.activities.filter(
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).order_by('-activity_date')
    
    other_activities = field.activities.exclude(
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).order_by('-activity_date')

    highest_bid = field.bids.aggregate(max_bid=Max('amount'))['max_bid']
    my_bids = field.bids.filter(millowner=request.user).order_by('-date')
    all_bids_count = field.bids.count()

    latest_harvest = harvest_activities.first()
    harvest_kg = None
    if latest_harvest and latest_harvest.yield_kg and latest_harvest.yield_kg > 0:
        harvest_kg = latest_harvest.yield_kg
    elif field.total_harvest_yield and field.total_harvest_yield > 0:
        harvest_kg = field.total_harvest_yield

    if request.method == 'POST':
        form = BidForm(request.POST, harvest_kg=harvest_kg)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.millowner = request.user
            bid.field = field

            entered_amount = bid.amount
            if harvest_kg and harvest_kg > 0:
                bid.per_kg_rate = entered_amount
                bid.amount = (entered_amount * Decimal(str(harvest_kg))).quantize(Decimal('0.01'))
                messages.success(
                    request,
                    f"Your bid offer of ₹{bid.amount} (₹{bid.per_kg_rate}/kg for {harvest_kg:g} kg) for {field.field_name} has been placed successfully!"
                )
            else:
                bid.per_kg_rate = None
                bid.amount = entered_amount
                messages.success(
                    request,
                    f"Your bid offer of ₹{bid.amount} for {field.field_name} has been placed successfully!"
                )
            bid.save()
            return redirect('millowner_field_detail', field_id=field.id)
    else:
        form = BidForm(harvest_kg=harvest_kg)

    return render(request, 'millowner/field_detail.html', {
        'field': field,
        'harvest_activities': harvest_activities,
        'latest_harvest': latest_harvest,
        'harvest_kg': harvest_kg,
        'other_activities': other_activities,
        'form': form,
        'highest_bid': highest_bid,
        'my_bids': my_bids,
        'all_bids_count': all_bids_count,
    })


@login_required
@role_required('MILLOWNER')
def millowner_bid_history(request):
    """
    Bid history page:
    Table of all bids placed by the logged-in mill owner, newest first.
    """
    bids = Bid.objects.filter(
        millowner=request.user
    ).select_related('field', 'field__owner', 'field__owner__farmer_profile').order_by('-date')

    total_bids = bids.count()
    total_amount = bids.aggregate(tot=Sum('amount'))['tot'] or 0

    return render(request, 'millowner/bid_history.html', {
        'bids': bids,
        'total_bids': total_bids,
        'total_amount': total_amount,
    })


@login_required
@role_required('MILLOWNER')
def millowner_field_harvest_pdf(request, field_id):
    """
    Generates and returns a PDF report of the harvest yield history
    for a specific field, viewed from the mill owner's perspective.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    field = get_object_or_404(
        Field.objects.select_related('owner', 'owner__farmer_profile'),
        id=field_id
    )

    harvest_activities = field.activities.filter(
        activity_type=FarmingActivity.ActivityType.HARVEST
    ).order_by('-activity_date')

    total_yield = harvest_activities.aggregate(total=Sum('yield_kg'))['total'] or 0
    farmer_name = (
        field.owner.farmer_profile.full_name
        if hasattr(field.owner, 'farmer_profile') and field.owner.farmer_profile.full_name
        else field.owner.username
    )
    farmer_id = (
        field.owner.farmer_profile.farmer_id
        if hasattr(field.owner, 'farmer_profile') and field.owner.farmer_profile.farmer_id
        else 'N/A'
    )

    # --- PDF Generation ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    GREEN_DARK = colors.HexColor('#1b4332')
    GREEN_MID  = colors.HexColor('#2d6a4f')
    GREEN_LIGHT = colors.HexColor('#d8f3dc')
    ACCENT     = colors.HexColor('#40916c')
    MUTED      = colors.HexColor('#6b7280')
    WHITE      = colors.white

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'],
        fontSize=20, textColor=WHITE, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=GREEN_LIGHT, alignment=TA_CENTER, spaceAfter=2)
    section_header_style = ParagraphStyle('SectionHeader', parent=styles['Normal'],
        fontSize=12, textColor=GREEN_DARK, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6)
    normal_style = ParagraphStyle('Normal2', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#374151'), leading=14)
    muted_style = ParagraphStyle('Muted', parent=styles['Normal'],
        fontSize=8, textColor=MUTED, leading=12)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold', textColor=GREEN_DARK)

    story = []

    # Header Banner
    header_data = [
        [Paragraph('PaddyNet', ParagraphStyle('H', parent=styles['Normal'],
            fontSize=22, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_LEFT)),
         Paragraph('Harvest Yield Report', ParagraphStyle('HR', parent=styles['Normal'],
            fontSize=13, fontName='Helvetica-Bold', textColor=GREEN_LIGHT, alignment=TA_RIGHT))]
    ]
    header_table = Table(header_data, colWidths=[9*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GREEN_DARK),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GREEN_DARK]),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (0,-1), 16),
        ('RIGHTPADDING', (-1,0), (-1,-1), 16),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Sub-header: generated date
    now_str = timezone.localtime(timezone.now()).strftime('%d %B %Y, %I:%M %p')
    story.append(Paragraph(f'Generated on: {now_str}  |  Viewed by: {request.user.username}',
        ParagraphStyle('Gen', parent=styles['Normal'], fontSize=8, textColor=MUTED, alignment=TA_RIGHT)))
    story.append(Spacer(1, 0.4*cm))

    # Field & Farmer Summary Box
    summary_data = [
        [Paragraph('<b>Field Name</b>', bold_style),
         Paragraph(field.field_name, normal_style),
         Paragraph('<b>Survey Code</b>', bold_style),
         Paragraph(field.field_identifier or '—', normal_style)],
        [Paragraph('<b>Location</b>', bold_style),
         Paragraph(field.location, normal_style),
         Paragraph('<b>Extent Area</b>', bold_style),
         Paragraph(f'{field.extent_area} Acres', normal_style)],
        [Paragraph('<b>Farmer Name</b>', bold_style),
         Paragraph(farmer_name, normal_style),
         Paragraph('<b>Farmer ID</b>', bold_style),
         Paragraph(farmer_id, normal_style)],
    ]
    summary_table = Table(summary_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 4.5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bbf7d0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # Total Yield Summary
    total_data = [
        [Paragraph('Total Harvest Yield (All Seasons)', ParagraphStyle('T', parent=styles['Normal'],
             fontSize=11, fontName='Helvetica-Bold', textColor=WHITE)),
         Paragraph(f'{float(total_yield):,.0f} kg', ParagraphStyle('TV', parent=styles['Normal'],
             fontSize=16, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT))]
    ]
    total_table = Table(total_data, colWidths=[12*cm, 5*cm])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (0,-1), 14),
        ('RIGHTPADDING', (-1,0), (-1,-1), 14),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.6*cm))

    # Harvest History Table
    story.append(Paragraph('Harvest Yield History', section_header_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=6))

    if harvest_activities.exists():
        col_headers = ['#', 'Harvest Date', 'Season / Year', 'Yield (kg)', 'Yield / Acre', 'Farmer Notes']
        table_data = [[Paragraph(f'<b>{h}</b>', ParagraphStyle('TH', parent=styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER))
            for h in col_headers]]

        for idx, ha in enumerate(harvest_activities, 1):
            yield_val = float(ha.yield_kg) if ha.yield_kg else None
            yield_str = f'{yield_val:,.0f} kg' if yield_val else 'Pending'
            per_acre = f'{yield_val / float(field.extent_area):,.1f} kg/ac' if (yield_val and field.extent_area > 0) else '—'
            row = [
                Paragraph(str(idx), muted_style),
                Paragraph(ha.activity_date.strftime('%d %b %Y'), normal_style),
                Paragraph(ha.season_year or '—', normal_style),
                Paragraph(f'<b>{yield_str}</b>',
                    ParagraphStyle('YV', parent=styles['Normal'], fontSize=9,
                        fontName='Helvetica-Bold', textColor=colors.HexColor('#15803d'))),
                Paragraph(per_acre, muted_style),
                Paragraph(ha.notes[:120] + ('...' if ha.notes and len(ha.notes) > 120 else '') if ha.notes else '—',
                    muted_style),
            ]
            table_data.append(row)

        harvest_table = Table(table_data,
            colWidths=[0.8*cm, 2.8*cm, 3.2*cm, 2.5*cm, 2.5*cm, 5.2*cm])
        harvest_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), GREEN_DARK),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, colors.HexColor('#f0fdf4')]),
            ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#d1fae5')),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (3,0), (4,-1), 'RIGHT'),
        ]))
        story.append(harvest_table)
    else:
        story.append(Paragraph('No harvest activities recorded for this field.', muted_style))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#d1d5db'), spaceAfter=6))
    story.append(Paragraph(
        'This report is auto-generated by PaddyNet — Agricultural Produce Management Platform. '
        'Data reflects records as of the report generation timestamp.',
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7.5, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    safe_name = field.field_name.replace(' ', '_')
    filename = f'HarvestReport_{safe_name}_Field{field_id}.pdf'
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
