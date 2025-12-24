
import os
import sys
import django
from django.conf import settings

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings_dev')
django.setup()

from apps.blog.models import Post
from apps.seo.models import SEOModel, Metadata
from apps.tags.models import Tag

def verify_automation():
    print("Verifying Automation Workflows...")
    
    posts = Post.objects.all().order_by('-id')[:10]
    if not posts:
        print("No posts found.")
        return

    for post in posts:
        print(f"\nChecking Post: {post.title} (ID: {post.id})")
        
        # 1. Check SEO Metadata
        try:
            # SEOModel is linked via GenericForeignKey, but we can query it directly
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(Post)
            seo = SEOModel.objects.filter(content_type=ct, object_id=post.id).first()
            
            if seo:
                meta = Metadata.objects.filter(seo=seo).first()
                if meta:
                    print(f"  [PASS] SEO Metadata found: Title='{meta.meta_title}'")
                else:
                    print("  [FAIL] SEO Object exists but Metadata missing.")
            else:
                print("  [FAIL] No SEO Object found.")
        except Exception as e:
            print(f"  [ERROR] Checking SEO: {e}")

        # 2. Check Auto Tags
        tags = post.tags.all()
        if tags.exists():
            tag_names = ", ".join([t.name for t in tags])
            print(f"  [PASS] Tags found: {tag_names}")
        else:
            print("  [FAIL] No tags assigned.")

if __name__ == "__main__":
    verify_automation()
