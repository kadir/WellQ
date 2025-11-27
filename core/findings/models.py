import uuid
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

# 1. WORKSPACE (The Team)
class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# 2. PRODUCT (The Repo/Asset)
class Product(models.Model):
    PRODUCT_TYPES = [
        ('WEB', 'Web Application'),
        ('API', 'API Service'),
        ('MOBILE', 'Mobile App'),
        ('LIBRARY', 'Software Library'),
        ('IOT', 'IoT Device Firmware'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # RELATED_NAME='products' is critical for the dashboard query!
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='products')
    
    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='WEB')
    tags = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 3. RELEASE (The Version - v1.0)
class Release(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='releases')
    
    name = models.CharField(max_length=100) # e.g. "v1.0.4"
    commit_hash = models.CharField(max_length=64, blank=True)
    sbom_file = models.FileField(upload_to='sboms/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} @ {self.name}"

# 4. SCAN (The Event)
class Scan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='scans')
    
    scanner_name = models.CharField(max_length=50)
    started_at = models.DateTimeField(default=timezone.now)

# 5. FINDING (The Vulnerability)
class Finding(models.Model):
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Info'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name='findings')
    
    title = models.CharField(max_length=500)
    cve_id = models.CharField(max_length=50, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField(blank=True)
    
    package_name = models.CharField(max_length=200)
    package_version = models.CharField(max_length=100)
    fixed_version = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cve_id} in {self.package_name}"