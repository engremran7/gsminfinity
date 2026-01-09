"""
Public views for firmware browsing, detail, and download pages.
"""
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .models import (
    Brand,
    EngineeringFirmware,
    Model,
    ModifiedFirmware,
    OfficialFirmware,
    OtherFirmware,
    ReadbackFirmware,
    Variant,
)

logger = logging.getLogger(__name__)

# Firmware type mapping
FIRMWARE_TYPES = {
    'official': OfficialFirmware,
    'officialfirmware': OfficialFirmware,
    'engineering': EngineeringFirmware,
    'engineeringfirmware': EngineeringFirmware,
    'readback': ReadbackFirmware,
    'readbackfirmware': ReadbackFirmware,
    'modified': ModifiedFirmware,
    'modifiedfirmware': ModifiedFirmware,
    'other': OtherFirmware,
    'otherfirmware': OtherFirmware,
}

FIRMWARE_TYPE_DISPLAY = {
    'official': 'Official',
    'officialfirmware': 'Official',
    'engineering': 'Engineering',
    'engineeringfirmware': 'Engineering',
    'readback': 'Readback',
    'readbackfirmware': 'Readback',
    'modified': 'Modified',
    'modifiedfirmware': 'Modified',
    'other': 'Other',
    'otherfirmware': 'Other',
}


def get_firmware_model(firmware_type: str):
    """Get the firmware model class from type string."""
    return FIRMWARE_TYPES.get(firmware_type.lower())


def get_all_firmwares_for_model(model_obj):
    """Get all firmware types for a given device model."""
    firmwares = []
    for type_key, model_class in [
        ('official', OfficialFirmware),
        ('engineering', EngineeringFirmware),
        ('readback', ReadbackFirmware),
        ('modified', ModifiedFirmware),
        ('other', OtherFirmware),
    ]:
        qs = model_class.objects.filter(
            model=model_obj,
            is_active=True
        ).select_related('brand', 'model', 'variant').order_by('-created_at')
        for fw in qs:
            fw.firmware_type = type_key
            fw.firmware_type_display = FIRMWARE_TYPE_DISPLAY[type_key]
            firmwares.append(fw)
    return firmwares


# ============================================================
# Browse / List Views
# ============================================================

@require_GET
def firmware_browse(request: HttpRequest) -> HttpResponse:
    """Main firmware browsing page with filters."""
    # Get all brands with firmware count
    brands = Brand.objects.all().order_by('name')

    # Get filter parameters
    brand_slug = request.GET.get('brand')
    firmware_type = request.GET.get('type', 'all')
    chipset = request.GET.get('chipset')
    search = request.GET.get('q', '').strip()

    # Build queryset based on type
    if firmware_type == 'all' or not firmware_type:
        # Get from all types
        all_firmwares = []
        for type_key, model_class in FIRMWARE_TYPES.items():
            if type_key in ['official', 'engineering', 'readback', 'modified', 'other']:
                qs = model_class.objects.filter(is_active=True).select_related('brand', 'model', 'variant')

                if brand_slug:
                    qs = qs.filter(brand__slug=brand_slug)
                if chipset:
                    qs = qs.filter(chipset__icontains=chipset)
                if search:
                    qs = qs.filter(
                        Q(original_file_name__icontains=search) |
                        Q(model__name__icontains=search) |
                        Q(brand__name__icontains=search) |
                        Q(chipset__icontains=search)
                    )

                for fw in qs:
                    fw.firmware_type = type_key
                    fw.firmware_type_display = FIRMWARE_TYPE_DISPLAY[type_key]
                    all_firmwares.append(fw)

        # Sort by created_at
        all_firmwares.sort(key=lambda x: x.created_at, reverse=True)
        firmwares_list = all_firmwares
    else:
        model_class = get_firmware_model(firmware_type)
        if not model_class:
            raise Http404("Invalid firmware type")

        qs = model_class.objects.filter(is_active=True).select_related('brand', 'model', 'variant')

        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)
        if chipset:
            qs = qs.filter(chipset__icontains=chipset)
        if search:
            qs = qs.filter(
                Q(original_file_name__icontains=search) |
                Q(model__name__icontains=search) |
                Q(brand__name__icontains=search) |
                Q(chipset__icontains=search)
            )

        firmwares_list = list(qs.order_by('-created_at'))
        for fw in firmwares_list:
            fw.firmware_type = firmware_type
            fw.firmware_type_display = FIRMWARE_TYPE_DISPLAY.get(firmware_type, firmware_type)

    # Pagination
    paginator = Paginator(firmwares_list, 20)
    page = request.GET.get('page', 1)
    firmwares = paginator.get_page(page)

    # Get unique chipsets for filter
    chipsets = set()
    for type_key, model_class in FIRMWARE_TYPES.items():
        if type_key in ['official', 'engineering', 'readback', 'modified', 'other']:
            for c in model_class.objects.filter(is_active=True).values_list('chipset', flat=True).distinct():
                if c:
                    chipsets.add(c)

    context = {
        'firmwares': firmwares,
        'brands': brands,
        'chipsets': sorted(chipsets),
        'selected_brand': brand_slug,
        'selected_type': firmware_type,
        'selected_chipset': chipset,
        'search_query': search,
        'firmware_types': [
            ('all', 'All Types'),
            ('official', 'Official'),
            ('engineering', 'Engineering'),
            ('readback', 'Readback'),
            ('modified', 'Modified'),
            ('other', 'Other'),
        ],
    }
    return render(request, 'firmwares/browse.html', context)


@require_GET
def brand_list(request: HttpRequest) -> HttpResponse:
    """List all brands grouped by alphabet."""
    brands = Brand.objects.all().order_by('name')

    # Add firmware counts and group by first letter
    total_firmwares = 0
    total_models = 0
    brands_by_letter = {}

    for brand in brands:
        brand.firmware_count = sum([
            OfficialFirmware.objects.filter(brand=brand, is_active=True).count(),
            EngineeringFirmware.objects.filter(brand=brand, is_active=True).count(),
            ReadbackFirmware.objects.filter(brand=brand, is_active=True).count(),
            ModifiedFirmware.objects.filter(brand=brand, is_active=True).count(),
            OtherFirmware.objects.filter(brand=brand, is_active=True).count(),
        ])
        brand.model_count = Model.objects.filter(brand=brand, is_active=True).count()
        total_firmwares += brand.firmware_count
        total_models += brand.model_count

        # Group by first letter
        first_letter = brand.name[0].upper() if brand.name else '#'
        if not first_letter.isalpha():
            first_letter = '#'
        if first_letter not in brands_by_letter:
            brands_by_letter[first_letter] = []
        brands_by_letter[first_letter].append(brand)

    # Sort letters alphabetically (# at the end)
    sorted_letters = sorted([l for l in brands_by_letter.keys() if l != '#'])
    if '#' in brands_by_letter:
        sorted_letters.append('#')

    # Create ordered dict of brands by letter
    grouped_brands = [(letter, brands_by_letter[letter]) for letter in sorted_letters]

    context = {
        'brands': brands,
        'grouped_brands': grouped_brands,
        'alphabet': sorted_letters,
        'total_firmwares': total_firmwares,
        'total_models': total_models,
    }
    return render(request, 'firmwares/brand_list.html', context)


@require_GET
def brand_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Brand detail page with all models."""
    brand = get_object_or_404(Brand, slug=slug)
    models = Model.objects.filter(brand=brand, is_active=True).order_by('name')

    # Add firmware counts to models
    total_firmwares = 0
    for model in models:
        model.firmware_count = sum([
            OfficialFirmware.objects.filter(model=model, is_active=True).count(),
            EngineeringFirmware.objects.filter(model=model, is_active=True).count(),
            ReadbackFirmware.objects.filter(model=model, is_active=True).count(),
            ModifiedFirmware.objects.filter(model=model, is_active=True).count(),
            OtherFirmware.objects.filter(model=model, is_active=True).count(),
        ])
        total_firmwares += model.firmware_count

    # Get other brands for sidebar
    other_brands = Brand.objects.exclude(id=brand.id).order_by('name')[:12]

    context = {
        'brand': brand,
        'models': models,
        'total_firmwares': total_firmwares,
        'other_brands': other_brands,
    }
    return render(request, 'firmwares/brand_detail.html', context)


@require_GET
def model_detail(request: HttpRequest, brand_slug: str, model_slug: str) -> HttpResponse:
    """Model detail page with all firmwares."""
    brand = get_object_or_404(Brand, slug=brand_slug)
    model = get_object_or_404(Model, brand=brand, slug=model_slug)
    variants = Variant.objects.filter(model=model, is_active=True).order_by('name')

    # Get all firmwares for this model
    firmwares = get_all_firmwares_for_model(model)

    # Add file size display to each firmware
    for fw in firmwares:
        if fw.file_size:
            if fw.file_size >= 1073741824:
                fw.file_size_display = f"{fw.file_size / 1073741824:.2f} GB"
            elif fw.file_size >= 1048576:
                fw.file_size_display = f"{fw.file_size / 1048576:.2f} MB"
            else:
                fw.file_size_display = f"{fw.file_size / 1024:.2f} KB"
        else:
            fw.file_size_display = "Unknown"

    # Get available firmware types
    firmware_types = list(set(fw.firmware_type for fw in firmwares))

    context = {
        'brand': brand,
        'model': model,
        'variants': variants,
        'firmwares': firmwares,
        'total_firmwares': len(firmwares),
        'firmware_types': firmware_types,
    }
    return render(request, 'firmwares/model_detail.html', context)


# ============================================================
# Firmware Detail View
# ============================================================

@require_GET
def firmware_detail(request: HttpRequest, firmware_type: str, firmware_id: str) -> HttpResponse:
    """Firmware detail page."""
    model_class = get_firmware_model(firmware_type)
    if not model_class:
        raise Http404("Invalid firmware type")

    firmware = get_object_or_404(
        model_class.objects.select_related('brand', 'model', 'variant', 'uploader'),
        id=firmware_id,
        is_active=True
    )

    # Increment view count
    model_class.objects.filter(id=firmware_id).update(view_count=F('view_count') + 1)

    # Get related firmwares (same model, different files)
    related_firmwares = []
    if firmware.model:
        related_firmwares = get_all_firmwares_for_model(firmware.model)
        # Exclude current firmware
        related_firmwares = [f for f in related_firmwares if str(f.id) != str(firmware_id)][:5]

    # Format file size
    if firmware.file_size:
        if firmware.file_size >= 1073741824:  # 1 GB
            file_size_display = f"{firmware.file_size / 1073741824:.2f} GB"
        elif firmware.file_size >= 1048576:  # 1 MB
            file_size_display = f"{firmware.file_size / 1048576:.2f} MB"
        elif firmware.file_size >= 1024:  # 1 KB
            file_size_display = f"{firmware.file_size / 1024:.2f} KB"
        else:
            file_size_display = f"{firmware.file_size} bytes"
    else:
        file_size_display = "Unknown"

    context = {
        'firmware': firmware,
        'firmware_type': firmware_type,
        'firmware_type_display': FIRMWARE_TYPE_DISPLAY.get(firmware_type, firmware_type),
        'related_firmwares': related_firmwares,
        'file_size_display': file_size_display,
    }
    return render(request, 'firmwares/firmware_detail.html', context)


# ============================================================
# Download Views
# ============================================================

@require_GET
def firmware_download(request: HttpRequest, firmware_type: str, firmware_id: str) -> HttpResponse:
    """Firmware download page with countdown/ad."""
    model_class = get_firmware_model(firmware_type)
    if not model_class:
        raise Http404("Invalid firmware type")

    firmware = get_object_or_404(
        model_class.objects.select_related('brand', 'model', 'variant'),
        id=firmware_id,
        is_active=True
    )

    # Format file size
    if firmware.file_size:
        if firmware.file_size >= 1073741824:
            file_size_display = f"{firmware.file_size / 1073741824:.2f} GB"
        elif firmware.file_size >= 1048576:
            file_size_display = f"{firmware.file_size / 1048576:.2f} MB"
        else:
            file_size_display = f"{firmware.file_size / 1024:.2f} KB"
    else:
        file_size_display = "Unknown"

    context = {
        'firmware': firmware,
        'firmware_type': firmware_type,
        'firmware_type_display': FIRMWARE_TYPE_DISPLAY.get(firmware_type, firmware_type),
        'file_size_display': file_size_display,
    }
    return render(request, 'firmwares/download.html', context)


@require_GET
def firmware_download_start(request: HttpRequest, firmware_type: str, firmware_id: str) -> HttpResponse:
    """Start actual download - increment count and redirect to file."""
    model_class = get_firmware_model(firmware_type)
    if not model_class:
        raise Http404("Invalid firmware type")

    firmware = get_object_or_404(
        model_class,
        id=firmware_id,
        is_active=True
    )

    # Increment download count
    model_class.objects.filter(id=firmware_id).update(download_count=F('download_count') + 1)

    # Log download
    logger.info(f"Firmware download started: {firmware.original_file_name} by {request.user if request.user.is_authenticated else 'anonymous'}")

    # For now, redirect to stored file path
    # In production, this would be a signed URL or storage backend redirect
    if firmware.stored_file_path:
        # If it's a full URL, redirect to it
        if firmware.stored_file_path.startswith(('http://', 'https://')):
            return redirect(firmware.stored_file_path)
        else:
            # Return a placeholder response for local files
            messages.info(request, f"Download would start for: {firmware.original_file_name}")
            return redirect('firmwares:firmware_detail', firmware_type=firmware_type, firmware_id=firmware_id)
    else:
        messages.error(request, "File not available for download.")
        return redirect('firmwares:firmware_detail', firmware_type=firmware_type, firmware_id=firmware_id)


# ============================================================
# API Endpoints for AJAX
# ============================================================

@require_GET
def api_firmware_stats(request: HttpRequest, firmware_type: str, firmware_id: str) -> JsonResponse:
    """Get firmware stats (views, downloads)."""
    model_class = get_firmware_model(firmware_type)
    if not model_class:
        return JsonResponse({'error': 'Invalid firmware type'}, status=404)

    try:
        firmware = model_class.objects.get(id=firmware_id)
        return JsonResponse({
            'views': firmware.view_count,
            'downloads': firmware.download_count,
        })
    except model_class.DoesNotExist:
        return JsonResponse({'error': 'Firmware not found'}, status=404)


@require_GET
def api_search_autocomplete(request: HttpRequest) -> JsonResponse:
    """
    Global search autocomplete API.
    Returns matching brands, models, variants, and firmwares.
    
    Searchable fields by type:
    - Brands: name, slug
    - Models: name, slug, marketing_name, model_code, description
    - Variants: name, slug, region, board_id, chipset
    - Firmwares: original_file_name, chipset, android_version, build_number,
                 + related brand/model/variant names and model codes
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # all, brands, models, firmwares, blog
    limit = min(int(request.GET.get('limit', 10)), 20)

    if len(query) < 2:
        return JsonResponse({'results': [], 'query': query})

    results = []

    # Search Brands
    if search_type in ('all', 'brands'):
        brands = Brand.objects.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        ).order_by('name')[:limit]

        for brand in brands:
            model_count = brand.models.count()
            results.append({
                'type': 'brand',
                'id': brand.id,
                'name': brand.name,
                'slug': brand.slug,
                'url': reverse('firmwares:brand_detail', args=[brand.slug]),
                'icon': 'building',
                'subtitle': f'{model_count} model{"s" if model_count != 1 else ""}',
            })

    # Search Models - includes marketing_name, model_code, description
    if search_type in ('all', 'models'):
        models_qs = Model.objects.filter(
            Q(name__icontains=query) |
            Q(slug__icontains=query) |
            Q(marketing_name__icontains=query) |
            Q(model_code__icontains=query) |
            Q(description__icontains=query) |
            Q(brand__name__icontains=query),
            is_active=True
        ).select_related('brand').order_by('name')[:limit]

        for model in models_qs:
            # Build informative subtitle
            subtitle_parts = [model.brand.name]
            if model.model_code:
                subtitle_parts.append(model.model_code)

            results.append({
                'type': 'model',
                'id': model.id,
                'name': model.marketing_name if model.marketing_name else model.name,
                'slug': model.slug,
                'url': reverse('firmwares:model_detail', args=[model.brand.slug, model.slug]),
                'icon': 'smartphone',
                'subtitle': ' • '.join(subtitle_parts),
                'brand': model.brand.name,
                'model_code': model.model_code or '',
                'marketing_name': model.marketing_name or '',
            })

    # Search Variants - includes region, board_id, chipset
    if search_type in ('all', 'variants'):
        from .models import Variant
        variants_qs = Variant.objects.filter(
            Q(name__icontains=query) |
            Q(slug__icontains=query) |
            Q(region__icontains=query) |
            Q(board_id__icontains=query) |
            Q(chipset__icontains=query) |
            Q(model__name__icontains=query) |
            Q(model__model_code__icontains=query) |
            Q(model__brand__name__icontains=query),
            is_active=True
        ).select_related('model', 'model__brand').order_by('name')[:limit]

        for variant in variants_qs:
            # Build informative subtitle
            subtitle_parts = []
            if variant.model and variant.model.brand:
                subtitle_parts.append(f'{variant.model.brand.name} {variant.model.name}')
            if variant.chipset:
                subtitle_parts.append(variant.chipset)
            if variant.region:
                subtitle_parts.append(variant.region)

            results.append({
                'type': 'variant',
                'id': variant.id,
                'name': variant.name,
                'slug': variant.slug,
                'url': reverse('firmwares:model_detail', args=[
                    variant.model.brand.slug if variant.model and variant.model.brand else '',
                    variant.model.slug if variant.model else ''
                ]),
                'icon': 'layers',
                'subtitle': ' • '.join(subtitle_parts) if subtitle_parts else 'Variant',
                'chipset': variant.chipset or '',
                'region': variant.region or '',
            })

    # Search Firmwares - comprehensive search across all firmware fields
    if search_type in ('all', 'firmwares'):
        remaining = limit - len(results) if search_type == 'all' else limit
        if remaining > 0:
            for type_key, model_class in [
                ('official', OfficialFirmware),
                ('engineering', EngineeringFirmware),
            ]:
                if remaining <= 0:
                    break

                # Comprehensive firmware search including:
                # - File name, chipset, android version, build number
                # - Related brand name
                # - Related model name, model_code, marketing_name
                # - Related variant name, region, chipset
                firmwares = model_class.objects.filter(
                    Q(original_file_name__icontains=query) |
                    Q(chipset__icontains=query) |
                    Q(android_version__icontains=query) |
                    Q(build_number__icontains=query) |
                    Q(brand__name__icontains=query) |
                    Q(model__name__icontains=query) |
                    Q(model__model_code__icontains=query) |
                    Q(model__marketing_name__icontains=query) |
                    Q(variant__name__icontains=query) |
                    Q(variant__region__icontains=query) |
                    Q(variant__chipset__icontains=query),
                    is_active=True
                ).select_related('brand', 'model', 'variant')[:remaining]

                for fw in firmwares:
                    # Build informative subtitle
                    subtitle_parts = []
                    if fw.brand:
                        subtitle_parts.append(fw.brand.name)
                    if fw.model:
                        subtitle_parts.append(fw.model.name)
                    if fw.variant:
                        subtitle_parts.append(fw.variant.name)
                    if fw.chipset:
                        subtitle_parts.append(fw.chipset)

                    results.append({
                        'type': 'firmware',
                        'id': str(fw.id),
                        'name': fw.original_file_name[:60] + ('...' if len(fw.original_file_name) > 60 else ''),
                        'url': reverse('firmwares:firmware_detail', args=[type_key, fw.id]),
                        'icon': 'cpu',
                        'subtitle': ' • '.join(subtitle_parts[:3]) if subtitle_parts else type_key.title(),
                        'firmware_type': type_key,
                        'chipset': fw.chipset or '',
                        'android_version': fw.android_version or '',
                    })
                    remaining -= 1

    # Search Blog Posts
    if search_type in ('all', 'blog'):
        remaining = limit - len(results) if search_type == 'all' else limit
        if remaining > 0:
            try:
                from django.utils import timezone as tz

                from apps.blog.models import Post

                # Search by title, summary, category name, and tags
                # Note: Body content search is intentionally excluded for autocomplete
                # as it's too expensive and returns too many irrelevant results.
                # Full-text body search should be done on the actual search results page.
                posts = Post.objects.filter(
                    Q(title__icontains=query) |
                    Q(summary__icontains=query) |
                    Q(category__name__icontains=query) |
                    Q(tags__name__icontains=query),
                    status='published',
                    publish_at__lte=tz.now()
                ).select_related('category').prefetch_related('tags').distinct().order_by('-published_at')[:remaining]

                for post in posts:
                    # Get tag names for subtitle
                    tag_names = [t.name for t in post.tags.all()[:3]]
                    subtitle_parts = []
                    if post.category:
                        subtitle_parts.append(post.category.name)
                    if tag_names:
                        subtitle_parts.append(', '.join(tag_names))
                    if post.published_at:
                        subtitle_parts.append(post.published_at.strftime('%b %d, %Y'))

                    results.append({
                        'type': 'blog',
                        'id': post.id,
                        'name': post.title,
                        'slug': post.slug,
                        'url': reverse('blog:post_detail', args=[post.slug]),
                        'icon': 'file-text',
                        'subtitle': ' • '.join(subtitle_parts) if subtitle_parts else 'Blog Post',
                    })
            except Exception as e:
                logger.warning(f"Blog search failed: {e}")

    return JsonResponse({
        'results': results[:limit],
        'query': query,
        'count': len(results),
    })
