"""
Firmware Blog Automation Service
Automatically creates blog posts for firmware uploads
Generates well-structured content with SEO optimization

TWO TYPES OF BLOG POSTS:
1. Manual Posts: Created by admins/users through blog interface
2. Auto-Generated Posts: Created automatically when firmware is uploaded
   - Marked with is_ai_generated=True flag
   - Category structure: Brand (parent) → Model (child)
   - Auto-updates when new firmware files added
   - Integrated with distribution system for multi-platform publishing
"""

import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class FirmwareBlogService:
    """Handles automatic blog post generation for firmware uploads"""

    @classmethod
    def get_auto_generated_posts(cls):
        """Get all auto-generated firmware posts (vs manual posts)"""
        if not apps.is_installed("apps.blog"):
            return None

        try:
            Post = apps.get_model("blog", "Post")
            return Post.objects.filter(is_ai_generated=True, is_published=True)
        except Exception as e:
            logger.error(f"Error getting auto-generated posts: {e}")
            return None

    @classmethod
    def get_manual_posts(cls):
        """Get all manually created posts (vs auto-generated)"""
        if not apps.is_installed("apps.blog"):
            return None

        try:
            Post = apps.get_model("blog", "Post")
            return Post.objects.filter(is_ai_generated=False, is_published=True)
        except Exception as e:
            logger.error(f"Error getting manual posts: {e}")
            return None

    @classmethod
    def ensure_brand_category(cls, brand):
        """Create or get blog category for brand"""
        if not apps.is_installed("apps.blog"):
            return None

        try:
            Category = apps.get_model("blog", "Category")

            category, created = Category.objects.get_or_create(
                slug=f"brand-{brand.slug}",
                defaults={
                    "name": f"{brand.name} Firmware",
                },
            )

            if created:
                logger.info(f"Created blog category for brand: {brand.name}")

            return category
        except Exception as e:
            logger.error(f"Error creating brand category: {e}")
            return None

    @classmethod
    def ensure_model_category(cls, model):
        """Create or get blog category for model (as child of brand category)"""
        if not apps.is_installed("apps.blog"):
            return None

        try:
            Category = apps.get_model("blog", "Category")

            # Ensure parent brand category exists first
            parent_category = cls.ensure_brand_category(model.brand)

            category, created = Category.objects.get_or_create(
                slug=f"model-{model.slug}",
                defaults={
                    "name": f"{model.name}",  # Just model name, brand is in parent
                    "parent": parent_category,
                },
            )

            # Update parent if it was created without one
            if not created and category.parent != parent_category:
                category.parent = parent_category
                category.save(update_fields=["parent"])

            if created:
                logger.info(
                    f"Created blog category for model: {model.name} under {model.brand.name}"
                )

            return category
        except Exception as e:
            logger.error(f"Error creating model category: {e}")
            return None

    @classmethod
    def generate_firmware_post(cls, model, force_update=False):
        """
        Generate or update blog post for a model listing all available firmwares

        Args:
            model: Model instance
            force_update: If True, regenerate content even if post exists
        """
        if not apps.is_installed("apps.blog"):
            logger.warning("Blog app not installed - skipping post generation")
            return None

        try:
            Post = apps.get_model("blog", "Post")
            apps.get_model("tags", "Tag")

            # Gather all firmwares for this model across all variants
            firmware_data = cls._collect_firmware_data(model)

            if not firmware_data["total_files"] and not force_update:
                logger.info(f"No firmware files for {model.name} - skipping post")
                return None

            # Generate post content
            post_slug = slugify(f"{model.brand.slug}-{model.slug}-firmware-download")
            title = f"{model.brand.name} {model.name} Firmware Download - All Variants"

            # Check if post exists
            existing_post = Post.objects.filter(slug=post_slug).first()

            if existing_post:
                # Update existing post (whether force_update or normal update)
                category = cls.ensure_model_category(model)

                existing_post.body = cls._generate_post_body(model, firmware_data)
                existing_post.summary = cls._generate_summary(model, firmware_data)
                existing_post.updated_at = timezone.now()
                existing_post.category = (
                    category  # Update category with new parent structure
                )
                existing_post.is_ai_generated = True  # Mark as auto-generated
                existing_post.save()

                cls._update_post_tags(existing_post, model, firmware_data)
                cls._update_post_seo(existing_post, model, firmware_data)

                # Create/update distribution plan
                cls._create_distribution_plan(existing_post, model, firmware_data)

                logger.info(f"Updated blog post for {model.name}")
                return existing_post

            # Create new post only if it doesn't exist
            category = cls.ensure_model_category(model)
            cls.ensure_brand_category(model.brand)

            # Get system user for author (or first superuser)
            from django.contrib.auth import get_user_model

            User = get_user_model()
            author = User.objects.filter(is_staff=True).first()

            if not author:
                logger.warning("No staff user found for blog post author")
                return None

            post = Post.objects.create(
                title=title,
                slug=post_slug,
                body=cls._generate_post_body(model, firmware_data),
                summary=cls._generate_summary(model, firmware_data),
                author=author,
                category=category,
                status="published",
                is_published=True,
                published_at=timezone.now(),
                allow_comments=True,
                # Mark as auto-generated firmware post
                is_ai_generated=True,  # Using this flag to identify auto-posts
            )

            # Add tags
            cls._update_post_tags(post, model, firmware_data)

            # Add SEO metadata
            cls._update_post_seo(post, model, firmware_data)

            # Create distribution plan for the blog post (multi-platform publishing)
            cls._create_distribution_plan(post, model, firmware_data)

            logger.info(f"Created new blog post for {model.name}")
            return post

        except Exception as e:
            logger.error(f"Error generating firmware post: {e}")
            return None

    @classmethod
    def _collect_firmware_data(cls, model):
        """Collect all firmware data for a model grouped by variant"""
        data = {
            "variants": [],
            "total_files": 0,
            "firmware_types": set(),
        }

        # Get all variants for this model
        variants = model.variants.all().select_related("model", "model__brand")

        for variant in variants:
            variant_data = {
                "variant": variant,
                "firmwares": [],
            }

            # Check all firmware types
            firmware_models = [
                ("OfficialFirmware", "Official"),
                ("EngineeringFirmware", "Engineering"),
                ("ReadbackFirmware", "Readback"),
                ("ModifiedFirmware", "Modified"),
                ("OtherFirmware", "Other"),
            ]

            for model_name, display_name in firmware_models:
                try:
                    FirmwareModel = apps.get_model("firmwares", model_name)
                    firmwares = FirmwareModel.objects.filter(variant=variant)

                    for fw in firmwares:
                        # Get storage location info if available
                        storage_info = cls._get_firmware_storage_info(fw)

                        variant_data["firmwares"].append(
                            {
                                "type": display_name,
                                "firmware": fw,
                                "chipset": fw.chipset or "N/A",
                                "file_name": fw.original_file_name,
                                "is_password_protected": fw.is_password_protected,
                                "storage_info": storage_info,
                            }
                        )
                        data["firmware_types"].add(display_name)
                        data["total_files"] += 1
                except Exception as e:
                    logger.debug(f"Error checking {model_name}: {e}")
                    continue

            if variant_data["firmwares"]:
                data["variants"].append(variant_data)

        return data

    @classmethod
    def _get_firmware_storage_info(cls, firmware):
        """Get storage/download information for firmware"""
        storage_info = {
            "is_uploaded": False,
            "file_size": None,
            "download_count": 0,
        }

        if not apps.is_installed("apps.storage"):
            return storage_info

        try:
            # Check if firmware has storage locations
            FirmwareStorageLocation = apps.get_model(
                "storage", "FirmwareStorageLocation"
            )

            # Get storage locations for this firmware
            locations = FirmwareStorageLocation.objects.filter(
                firmware_content_type=ContentType.objects.get_for_model(firmware),
                firmware_object_id=firmware.id,
            )

            if locations.exists():
                storage_info["is_uploaded"] = True
                # Get total download count
                storage_info["download_count"] = sum(
                    loc.download_count for loc in locations
                )
                # Get file size from first location
                first_loc = locations.first()
                if first_loc:
                    storage_info["file_size"] = first_loc.file_size_bytes

        except Exception as e:
            logger.debug(f"Error getting storage info: {e}")

        return storage_info

    @classmethod
    def _generate_post_body(cls, model, firmware_data):
        """Generate HTML content for blog post"""
        html_parts = []

        # Introduction
        html_parts.append(
            f"<h2>Download {model.brand.name} {model.name} Firmware - All Variants</h2>"
        )
        html_parts.append(
            f"<p>Complete collection of firmware files for <strong>{model.brand.name} {model.name}</strong>. "
        )
        html_parts.append(
            f"We have <strong>{firmware_data['total_files']} firmware files</strong> available across "
        )
        html_parts.append(
            f"<strong>{len(firmware_data['variants'])} variants</strong>.</p>"
        )

        # Firmware types available
        if firmware_data["firmware_types"]:
            types_list = ", ".join(sorted(firmware_data["firmware_types"]))
            html_parts.append(f"<p><strong>Available types:</strong> {types_list}</p>")

        # Auto-generated notice
        html_parts.append('<div class="alert alert-info">')
        html_parts.append(
            "📢 <strong>Auto-Updated Post:</strong> This firmware list is automatically updated "
        )
        html_parts.append(
            "whenever new files are uploaded. Check back regularly for the latest versions."
        )
        html_parts.append("</div>")

        html_parts.append("<hr>")

        # List firmwares by variant
        for variant_data in firmware_data["variants"]:
            variant = variant_data["variant"]
            firmwares = variant_data["firmwares"]

            html_parts.append(
                f"<h3>📱 {variant.name} ({variant.region or 'Global'})</h3>"
            )

            if variant.board_id:
                html_parts.append(
                    f"<p><strong>Board ID:</strong> <code>{variant.board_id}</code></p>"
                )

            html_parts.append(
                f"<p>Found <strong>{len(firmwares)} firmware file(s)</strong> for this variant:</p>"
            )

            # Firmware table
            html_parts.append('<div class="table-responsive">')
            html_parts.append('<table class="table table-bordered">')
            html_parts.append("<thead><tr>")
            html_parts.append("<th>Type</th>")
            html_parts.append("<th>File Name</th>")
            html_parts.append("<th>Chipset</th>")
            html_parts.append("<th>Size</th>")
            html_parts.append("<th>Downloads</th>")
            html_parts.append("<th>Status</th>")
            html_parts.append("<th>Action</th>")
            html_parts.append("</tr></thead>")
            html_parts.append("<tbody>")

            for fw_data in firmwares:
                fw = fw_data["firmware"]
                storage_info = fw_data["storage_info"]

                html_parts.append("<tr>")
                html_parts.append(
                    f'<td><span class="badge badge-primary">{fw_data["type"]}</span></td>'
                )
                html_parts.append(f"<td><code>{fw_data['file_name']}</code></td>")
                html_parts.append(f"<td>{fw_data['chipset']}</td>")

                # File size
                if storage_info["file_size"]:
                    size_gb = storage_info["file_size"] / (1024**3)
                    html_parts.append(f"<td>{size_gb:.2f} GB</td>")
                else:
                    html_parts.append("<td>N/A</td>")

                # Download count
                html_parts.append(f"<td>{storage_info['download_count']} times</td>")

                # Status
                if not storage_info["is_uploaded"]:
                    html_parts.append(
                        '<td><span class="badge badge-warning">⏳ Processing</span></td>'
                    )
                elif fw_data["is_password_protected"]:
                    html_parts.append(
                        '<td><span class="badge badge-info">🔒 Password Protected</span></td>'
                    )
                else:
                    html_parts.append(
                        '<td><span class="badge badge-success">✅ Ready</span></td>'
                    )

                # Download button with distribution integration
                if storage_info["is_uploaded"]:
                    download_url = f"/firmwares/{fw.id}/download/"
                    # Check if distribution app is available for multi-cloud download
                    if apps.is_installed("apps.distribution"):
                        download_url = f"/api/distribution/firmware/{fw.id}/download/"
                    html_parts.append(
                        f'<td><a href="{download_url}" class="btn btn-sm btn-primary">Download</a></td>'
                    )
                else:
                    html_parts.append(
                        '<td><button class="btn btn-sm btn-secondary" disabled>Processing...</button></td>'
                    )

                html_parts.append("</tr>")

            html_parts.append("</tbody></table>")
            html_parts.append("</div>")
            html_parts.append("<hr>")

        # Footer notes
        html_parts.append("<h4>⚠️ Important Notes</h4>")
        html_parts.append("<ul>")
        html_parts.append("<li>Always backup your data before flashing firmware</li>")
        html_parts.append(
            "<li>Ensure you download the correct firmware for your device variant</li>"
        )
        html_parts.append("<li>Check the chipset compatibility before flashing</li>")
        html_parts.append(
            "<li>Password-protected files require extraction password (contact support)</li>"
        )
        html_parts.append("</ul>")

        html_parts.append(
            f"<p><small>Last updated: {timezone.now().strftime('%B %d, %Y')}</small></p>"
        )

        return "".join(html_parts)

    @classmethod
    def _generate_summary(cls, model, firmware_data):
        """Generate post summary/excerpt"""
        summary = (
            f"Download {model.brand.name} {model.name} firmware for all variants. "
        )
        summary += f"{firmware_data['total_files']} firmware files available across "
        summary += f"{len(firmware_data['variants'])} variants. "

        if firmware_data["firmware_types"]:
            types = ", ".join(sorted(firmware_data["firmware_types"]))
            summary += f"Types: {types}."

        return summary

    @classmethod
    def _update_post_tags(cls, post, model, firmware_data):
        """
        Auto-generate and assign tags to post with configurable limits from DistributionSettings.
        Limits are managed in admin panel under Distribution > Distribution Settings.
        """
        if not apps.is_installed("apps.tags"):
            return

        try:
            Tag = apps.get_model("tags", "Tag")

            # Get limits from admin-configurable DistributionSettings
            try:
                if apps.is_installed("apps.distribution"):
                    DistributionSettings = apps.get_model(
                        "distribution", "DistributionSettings"
                    )
                    settings = DistributionSettings.get_solo()
                    MAX_AUTO_TAGS = settings.max_auto_tags
                else:
                    MAX_AUTO_TAGS = 15  # Fallback if distribution app not available
            except Exception as e:
                logger.debug(f"Could not load DistributionSettings: {e}")
                MAX_AUTO_TAGS = 15

            tags_to_add = []

            # Brand tag (priority 1)
            brand_tag, _ = Tag.objects.get_or_create(
                slug=slugify(model.brand.name), defaults={"name": model.brand.name}
            )
            tags_to_add.append(brand_tag)

            # Model tag (priority 2)
            model_tag, _ = Tag.objects.get_or_create(
                slug=slugify(f"{model.brand.name}-{model.name}"),
                defaults={"name": f"{model.brand.name} {model.name}"},
            )
            tags_to_add.append(model_tag)

            # Firmware type tags (priority 3) - limit to 3 most common types
            firmware_types = list(firmware_data["firmware_types"])[:3]
            for fw_type in firmware_types:
                type_tag, _ = Tag.objects.get_or_create(
                    slug=slugify(f"{fw_type}-firmware"),
                    defaults={"name": f"{fw_type} Firmware"},
                )
                tags_to_add.append(type_tag)

            # Chipset tags (priority 4) - extract from firmware variants
            chipsets = set()
            for variant_data in firmware_data.get("variants", []):
                for fw in variant_data.get("firmwares", []):
                    chipset = fw.get("chipset", "")
                    if chipset and chipset not in ("N/A", "Unknown", ""):
                        chipsets.add(chipset)

            for chipset in list(chipsets)[:3]:  # Limit to 3 chipsets
                chipset_tag, _ = Tag.objects.get_or_create(
                    slug=slugify(chipset), defaults={"name": chipset}
                )
                tags_to_add.append(chipset_tag)

            # Generic tags (priority 5) - only essential ones
            generic_tags = ["firmware", "download"]
            for tag_name in generic_tags:
                tag, _ = Tag.objects.get_or_create(
                    slug=slugify(tag_name),
                    defaults={"name": tag_name.replace("-", " ").title()},
                )
                tags_to_add.append(tag)

            # Apply limit from admin settings (configurable)
            tags_to_add = tags_to_add[:MAX_AUTO_TAGS]

            post.tags.set(tags_to_add)
            logger.info(
                f"Added {len(tags_to_add)} tags to post including {len(chipsets)} chipsets (max allowed: {MAX_AUTO_TAGS} - configurable in admin)"
            )

            # Sync tag usage counts
            try:
                from apps.tags.tasks import sync_tag_usage_counts

                tag_ids = list(post.tags.values_list("id", flat=True))
                if tag_ids:
                    sync_tag_usage_counts.delay(tag_ids)
            except Exception as e:
                logger.debug(f"Tag usage sync skipped: {e}")

        except Exception as e:
            logger.error(f"Error adding tags: {e}")

    @classmethod
    def _update_post_seo(cls, post, model, firmware_data):
        """
        Generate SEO metadata with configurable limits from DistributionSettings.
        Character limits are managed in admin panel under Distribution > Distribution Settings.
        """
        try:
            # Get SEO limits from admin-configurable DistributionSettings
            try:
                if apps.is_installed("apps.distribution"):
                    DistributionSettings = apps.get_model(
                        "distribution", "DistributionSettings"
                    )
                    settings = DistributionSettings.get_solo()
                    MAX_SEO_TITLE = settings.max_seo_title_length
                    MAX_SEO_DESC = settings.max_seo_description_length
                else:
                    MAX_SEO_TITLE = 60
                    MAX_SEO_DESC = 160
            except Exception:
                MAX_SEO_TITLE = 60
                MAX_SEO_DESC = 160

            # SEO Title
            seo_title = f"{model.brand.name} {model.name} Firmware Download"
            if len(seo_title) > MAX_SEO_TITLE:
                seo_title = f"{model.brand.name} {model.name} Firmware"
            if len(seo_title) > MAX_SEO_TITLE:
                seo_title = seo_title[: MAX_SEO_TITLE - 3] + "..."
            post.seo_title = seo_title

            # SEO Description
            seo_desc = f"Download {model.brand.name} {model.name} firmware files. "
            seo_desc += f"{firmware_data['total_files']} files across {len(firmware_data['variants'])} variants. "

            types = list(firmware_data["firmware_types"])[:2]
            if types:
                seo_desc += f"{', '.join(types)} available."

            if len(seo_desc) > MAX_SEO_DESC:
                seo_desc = seo_desc[: MAX_SEO_DESC - 3] + "..."

            post.seo_description = seo_desc
            post.save(update_fields=["seo_title", "seo_description"])

            logger.info(
                f"Updated SEO (title: {len(post.seo_title)}/{MAX_SEO_TITLE}, desc: {len(post.seo_description)}/{MAX_SEO_DESC})"
            )

        except Exception as e:
            logger.error(f"Error updating SEO: {e}")

    @classmethod
    def _create_distribution_plan(cls, post, model, firmware_data):
        """
        Create distribution plan using configurable limits from DistributionSettings.
        All limits are managed in admin panel: Distribution > Distribution Settings
        """
        if not apps.is_installed("apps.distribution"):
            return

        try:
            from django.contrib.contenttypes.models import ContentType

            ContentDistribution = apps.get_model("distribution", "ContentDistribution")
            DistributionSettings = apps.get_model(
                "distribution", "DistributionSettings"
            )

            settings = DistributionSettings.get_solo()

            if not settings.enable_firmware_auto_distribution:
                logger.info(
                    f"Firmware auto-distribution disabled - skipping: {post.title}"
                )
                return

            post_content_type = ContentType.objects.get_for_model(post)

            MAX_PLATFORMS = settings.max_platforms_per_content
            MAX_AUTO_TAGS = settings.max_auto_tags
            MAX_SEO_TAGS = settings.max_seo_tags

            target_channels = (
                settings.default_channels[:MAX_PLATFORMS]
                if settings.default_channels
                else ["twitter", "facebook", "telegram", "linkedin", "reddit"][
                    :MAX_PLATFORMS
                ]
            )

            post_tags = list(post.tags.values_list("name", flat=True))[:MAX_AUTO_TAGS]
            seo_tags = [post.seo_title, model.brand.name, model.name][:MAX_SEO_TAGS]

            distribution, created = ContentDistribution.objects.update_or_create(
                content_type=post_content_type,
                object_id=post.id,
                defaults={
                    "title": post.title[: settings.max_seo_title_length],
                    "summary": post.summary[: settings.max_seo_description_length]
                    if post.summary
                    else "",
                    "content_url": f"/blog/{post.slug}/",
                    "target_channels": target_channels,
                    "status": "pending",
                    "priority": 5,
                    "metadata": {
                        "tags": post_tags,
                        "seo_tags": seo_tags,
                        "brand": model.brand.name,
                        "model": model.name,
                        "firmware_count": firmware_data["total_files"],
                        "auto_generated": True,
                    },
                },
            )

            distribution.apply_limits()

            logger.info(
                f"{'Created' if created else 'Updated'} distribution plan: {post.title} ({len(target_channels)} platforms)"
            )

            try:
                from apps.distribution.tasks import distribute_content

                distribute_content.delay(distribution.id)
            except Exception as e:
                logger.debug(f"Could not queue distribution task: {e}")

        except Exception as e:
            logger.warning(f"Error creating distribution plan: {e}")
