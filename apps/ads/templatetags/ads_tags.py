
from __future__ import annotations

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from apps.ads.models import AdPlacement, AdsSettings
from apps.core.cache import cache
from apps.core.utils import feature_flags

register = template.Library()


def _ads_enabled() -> bool:
    try:
        return feature_flags.ads_enabled()
    except Exception:
        return False


def _get_ads_settings():
    """Get the ads settings singleton with caching."""
    try:
        return AdsSettings.get_solo()
    except Exception:
        return None


@register.simple_tag(takes_context=True)
def render_ad_slot(context, slug: str, allowed_types: str = "", allowed_sizes: str = ""):
    """
    Render an ad slot placeholder. Uses placement config when ads are enabled.
    Respects site feature flags and consent (if present on request).
    """
    if not _ads_enabled():
        return ""

    if not slug:
        # Invalid invocation – avoid hitting the database or cache.
        return ""

    request = context.get("request")

    # Check user exclusions
    settings_obj = _get_ads_settings()
    if settings_obj and request:
        user = getattr(request, 'user', None)
        page_url = request.path if hasattr(request, 'path') else ""
        if not settings_obj.should_show_ads(user=user, page_url=page_url):
            return ""

    consent_flags = getattr(request, "consent_flags", None)
    if consent_flags is not None:
        try:
            if not getattr(consent_flags, "allow_ads", True):
                # Check if we should show non-personalized ads
                if settings_obj and not settings_obj.show_ads_without_consent:
                    return ""
        except Exception:
            pass

    key_suffix = f"{allowed_types or '*'}|{allowed_sizes or '*'}"
    cache_key = f"ads_slot_{slug}:{key_suffix}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        placement = AdPlacement.objects.filter(slug=slug, is_active=True, is_enabled=True, is_deleted=False).first()
        html = render_to_string(
            "ads/components/slot.html",
            {
                "placement": placement,
                "fallback_slug": slug,
                "allowed_types": allowed_types or getattr(placement, "allowed_types", ""),
                "allowed_sizes": allowed_sizes or getattr(placement, "allowed_sizes", ""),
                "settings": settings_obj,
            },
            request=request,
        )
        # SECURITY: Django template auto-escapes all variables
        # Ad HTML from placement.html field should be pre-sanitized in model clean()
        safe_html = mark_safe(html)
        cache.set(cache_key, safe_html, 120)
        return safe_html
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to render ad slot {slug}: {e}")
        return ""


@register.simple_tag(takes_context=True)
def render_rewarded_ad(context, config_name: str = ""):
    """
    Render a rewarded ad button/trigger.
    Users can click to watch a video ad and earn rewards.
    """
    if not _ads_enabled():
        return ""

    settings_obj = _get_ads_settings()
    if not settings_obj or not settings_obj.rewarded_ads_enabled:
        return ""

    request = context.get("request")
    user = getattr(request, 'user', None) if request else None

    # Rewarded ads require authentication
    if not user or not user.is_authenticated:
        return ""

    try:
        from apps.ads.models import RewardedAdConfig

        if config_name:
            config = RewardedAdConfig.objects.filter(name=config_name, is_enabled=True).first()
        else:
            config = RewardedAdConfig.objects.filter(is_enabled=True).first()

        if not config:
            return ""

        html = render_to_string(
            "ads/components/rewarded_button.html",
            {
                "config": config,
                "user": user,
                "settings": settings_obj,
            },
            request=request,
        )
        return mark_safe(html)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to render rewarded ad: {e}")
        return ""


@register.simple_tag(takes_context=True)
def render_network_ads(context, network_type: str = "adsense"):
    """
    Render ad network scripts and auto-ad code.
    Supports: adsense, medianet, ezoic, etc.
    """
    if not _ads_enabled():
        return ""

    settings_obj = _get_ads_settings()
    if not settings_obj or not settings_obj.ad_networks_enabled:
        return ""

    request = context.get("request")

    try:
        if network_type == "adsense" and settings_obj.adsense_enabled:
            html = _render_adsense(settings_obj, request)
        elif network_type == "medianet" and settings_obj.medianet_enabled:
            html = _render_medianet(settings_obj, request)
        else:
            # Try to find network in AdNetwork model
            from apps.ads.models import AdNetwork
            network = AdNetwork.objects.filter(network_type=network_type, is_enabled=True).first()
            if network:
                html = network.header_script or ""
            else:
                return ""

        return mark_safe(html)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to render network ads ({network_type}): {e}")
        return ""


def _render_adsense(settings_obj, request) -> str:
    """Render Google AdSense code."""
    publisher_id = settings_obj.adsense_publisher_id
    if not publisher_id:
        return ""

    auto_ads = settings_obj.adsense_auto_ads

    html = f'''
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={publisher_id}" crossorigin="anonymous"></script>
    '''

    if auto_ads:
        html += '''
        <script>
            (adsbygoogle = window.adsbygoogle || []).push({
                google_ad_client: "''' + publisher_id + '''",
                enable_page_level_ads: true
            });
        </script>
        '''

    return html


def _render_medianet(settings_obj, request) -> str:
    """Render Media.net code."""
    customer_id = settings_obj.medianet_customer_id
    if not customer_id:
        return ""

    return f'''
    <script type="text/javascript">
        window._mNHandle = window._mNHandle || {{}};
        window._mNHandle.queue = window._mNHandle.queue || [];
        mediapolygon = window.mediaPolygon || null;
    </script>
    <script src="https://contextual.media.net/ctagconfig.js?cid={customer_id}" async="async"></script>
    '''


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def inject_ads(value, frequency=3):
    """
    Injects ad slots into HTML content after every `frequency` paragraphs.
    Usage: {{ post.body|inject_ads:3|safe }}
    """
    if not _ads_enabled():
        return value

    if not value:
        return ""

    settings_obj = _get_ads_settings()
    if settings_obj and not settings_obj.auto_ads_in_article:
        return value

    # Simple split by closing paragraph tag
    paragraphs = value.split('</p>')
    if len(paragraphs) <= frequency:
        return value

    new_content = []
    for i, p in enumerate(paragraphs):
        if not p.strip():
            continue

        new_content.append(p + '</p>')

        # Inject ad after every Nth paragraph, but not at the very end
        if (i + 1) % frequency == 0 and i < len(paragraphs) - 1:
            slot_num = (i + 1) // frequency
            # We can't easily call render_ad_slot here because we don't have context/request
            # So we inject a placeholder div that JS or a second pass could pick up.
            # OR better: we just render a generic slot structure directly if we can't access DB.
            # However, for this "intelligent" feature, let's try to render a real slot if possible.
            # Since we can't access 'context' in a filter easily without a custom tag,
            # we will inject a lazy-load marker that the frontend JS (ads.js) can hydrate.

            ad_html = f'''
            <div class="my-8 flex justify-center">
                <div class="ad-slot-in-content" data-ad-slot="in-content-{slot_num}" data-requires-consent="ads">
                    <!-- Placeholder for JS hydration -->
                    <div class="w-full max-w-2xl h-auto min-h-24 bg-[var(--color-bg-surface-secondary)] border border-dashed border-[var(--color-border-default)] rounded-lg flex items-center justify-center text-[var(--color-text-muted)] text-sm p-4">
                        <span class="text-xs opacity-75">Advertisement</span>
                    </div>
                </div>
            </div>
            '''
            new_content.append(ad_html)

    return mark_safe("".join(new_content))


@register.inclusion_tag("ads/components/header_scripts.html", takes_context=True)
def ads_header_scripts(context):
    """
    Render all enabled ad network header scripts.
    Include this in the <head> section of base.html.
    """
    settings_obj = _get_ads_settings()
    if not settings_obj or not settings_obj.ads_enabled:
        return {"render": False}

    request = context.get("request")

    # Collect all enabled network scripts
    networks = []

    if settings_obj.adsense_enabled and settings_obj.adsense_publisher_id:
        networks.append({
            "name": "adsense",
            "script": _render_adsense(settings_obj, request),
        })

    if settings_obj.medianet_enabled and settings_obj.medianet_customer_id:
        networks.append({
            "name": "medianet",
            "script": _render_medianet(settings_obj, request),
        })

    # Add custom networks from AdNetwork model
    try:
        from apps.ads.models import AdNetwork
        for network in AdNetwork.objects.filter(is_enabled=True).exclude(header_script=""):
            networks.append({
                "name": network.network_type,
                "script": network.header_script,
            })
    except Exception:
        pass

    return {
        "render": True,
        "networks": networks,
        "settings": settings_obj,
        "lazy_load": settings_obj.lazy_load_ads,
        "consent_required": settings_obj.require_consent,
    }


@register.simple_tag
def ads_consent_mode():
    """
    Return Google Consent Mode v2 configuration.
    """
    settings_obj = _get_ads_settings()
    if not settings_obj:
        return ""

    default = settings_obj.consent_mode_default

    return mark_safe(f'''
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('consent', 'default', {{
            'ad_storage': '{default}',
            'ad_user_data': '{default}',
            'ad_personalization': '{default}',
            'analytics_storage': '{default}'
        }});
    </script>
    ''')


# ==================== AFFILIATE PRODUCTS ====================

@register.inclusion_tag("ads/components/affiliate_products.html", takes_context=True)
def render_affiliate_products(
    context,
    brand=None,
    model=None,
    variant=None,
    blog_post=None,
    max_products=4,
    layout="grid",
    title="Recommended Products"
):
    """
    Render contextual affiliate product recommendations.
    
    Usage:
        {% render_affiliate_products brand=brand %}
        {% render_affiliate_products model=model max_products=6 %}
        {% render_affiliate_products blog_post=post layout="carousel" %}
    """
    settings_obj = _get_ads_settings()
    if not settings_obj or not settings_obj.affiliate_products_enabled:
        return {"render": False}

    # Check page-type specific settings
    if brand and not settings_obj.affiliate_products_show_on_brand:
        return {"render": False}
    if model and not settings_obj.affiliate_products_show_on_model:
        return {"render": False}
    if variant and not settings_obj.affiliate_products_show_on_firmware:
        return {"render": False}
    if blog_post and not settings_obj.affiliate_products_show_on_blog:
        return {"render": False}

    request = context.get("request")

    try:
        products = _get_contextual_products(
            brand=brand,
            model=model,
            variant=variant,
            blog_post=blog_post,
            max_products=min(max_products, settings_obj.affiliate_products_max_per_page),
            settings_obj=settings_obj,
        )

        return {
            "render": True,
            "products": products,
            "layout": layout,
            "title": title,
            "settings": settings_obj,
            "request": request,
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to render affiliate products: {e}")
        return {"render": False}


def _get_contextual_products(brand=None, model=None, variant=None, blog_post=None, max_products=4, settings_obj=None):
    """
    Get relevant affiliate products based on context.
    
    Priority:
    1. Manual matches (pinned first)
    2. Brand/model targeted products
    3. Keyword matches
    4. Universal products
    """
    from django.db.models import Q

    from apps.ads.models import AffiliateProduct, AffiliateProductMatch

    products = []
    seen_ids = set()

    # 1. First, get any manual matches (pinned products)
    match_filters = Q(is_hidden=False)
    if brand:
        match_filters &= Q(brand=brand)
    elif model:
        match_filters &= Q(model=model)
    elif variant:
        match_filters &= Q(variant=variant)
    elif blog_post:
        match_filters &= Q(blog_post=blog_post)

    manual_matches = AffiliateProductMatch.objects.filter(
        match_filters,
        product__is_enabled=True,
        product__is_in_stock=True,
    ).select_related("product", "product__provider").order_by("-is_pinned", "position", "-relevance_score")[:max_products]

    for match in manual_matches:
        if match.product_id not in seen_ids:
            products.append(match.product)
            seen_ids.add(match.product_id)

    if len(products) >= max_products:
        return products[:max_products]

    # 2. Get brand/model targeted products
    remaining = max_products - len(products)
    targeted_filters = Q(is_enabled=True, is_in_stock=True)
    targeted_filters &= ~Q(id__in=seen_ids)

    if brand:
        targeted_filters &= Q(target_brands=brand)
    elif model:
        targeted_filters &= (Q(target_models=model) | Q(target_brands=model.brand))
    elif variant and hasattr(variant, 'model') and variant.model:
        targeted_filters &= (Q(target_models=variant.model) | Q(target_brands=variant.model.brand))

    targeted_products = AffiliateProduct.objects.filter(targeted_filters).order_by(
        "-ai_relevance_score", "-rating"
    )[:remaining]

    for product in targeted_products:
        if product.id not in seen_ids:
            products.append(product)
            seen_ids.add(product.id)

    if len(products) >= max_products:
        return products[:max_products]

    # 3. Keyword matching
    remaining = max_products - len(products)
    keywords = []

    if brand:
        keywords.extend([brand.name.lower()])
    elif model:
        keywords.extend([model.name.lower(), model.brand.name.lower() if model.brand else ""])
    elif variant and hasattr(variant, 'model') and variant.model:
        keywords.extend([variant.model.name.lower()])
        if variant.model.brand:
            keywords.append(variant.model.brand.name.lower())
    elif blog_post:
        # Extract keywords from blog post title/tags
        keywords.append(blog_post.title.lower() if hasattr(blog_post, 'title') else "")

    if keywords:
        keyword_filters = Q(is_enabled=True, is_in_stock=True)
        keyword_filters &= ~Q(id__in=seen_ids)

        keyword_q = Q()
        for kw in keywords:
            if kw:
                keyword_q |= Q(target_keywords__icontains=kw)

        if keyword_q:
            keyword_products = AffiliateProduct.objects.filter(
                keyword_filters & keyword_q
            ).order_by("-ai_relevance_score", "-rating")[:remaining]

            for product in keyword_products:
                if product.id not in seen_ids:
                    products.append(product)
                    seen_ids.add(product.id)

    if len(products) >= max_products:
        return products[:max_products]

    # 4. Universal products as fallback
    remaining = max_products - len(products)
    universal_products = AffiliateProduct.objects.filter(
        is_enabled=True,
        is_in_stock=True,
        is_universal=True,
    ).exclude(id__in=seen_ids).order_by("-ai_relevance_score", "-rating")[:remaining]

    for product in universal_products:
        if product.id not in seen_ids:
            products.append(product)
            seen_ids.add(product.id)

    return products[:max_products]


@register.simple_tag(takes_context=True)
def track_affiliate_click(context, product):
    """
    Generate tracking URL for affiliate clicks.
    Returns the affiliate URL with tracking parameters.
    """
    if not product:
        return "#"

    request = context.get("request")

    try:
        # Build tracking URL
        base_url = product.affiliate_url or product.product_url

        # Add tracking parameters
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)

        # Add internal tracking
        params["_gsm_click"] = [str(product.id)]
        if request:
            params["_gsm_ref"] = [request.path[:100]]

        new_query = urlencode(params, doseq=True)
        tracked_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))

        return tracked_url
    except Exception:
        return product.affiliate_url or product.product_url or "#"


@register.inclusion_tag("ads/components/affiliate_product_card.html", takes_context=True)
def render_affiliate_product_card(context, product, size="medium"):
    """
    Render a single affiliate product card.
    
    Usage:
        {% render_affiliate_product_card product %}
        {% render_affiliate_product_card product size="small" %}
    """
    settings_obj = _get_ads_settings()
    return {
        "product": product,
        "size": size,
        "settings": settings_obj,
        "request": context.get("request"),
    }


