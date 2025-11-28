import uuid
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import hashlib

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
    # The specific types you requested
    PRODUCT_TYPES = [
        ('WEB', 'Web Application'),
        ('REPO', 'Code Repository'),
        ('IMAGE', 'Docker Image'),
        ('ANDROID', 'Android App'),
        ('IOS', 'iOS App'),
        ('BINARY', 'Binary Executable'),
    ]

    IMPACT_CHOICES = [
        ('CRITICAL', 'Critical (Tier 1)'),
        ('HIGH', 'High (Tier 2)'),
        ('MEDIUM', 'Medium (Tier 3)'),
        ('LOW', 'Low (Tier 4)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='products')
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Updated field with choices
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='WEB')
    
    criticality = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='MEDIUM')
    tags = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 3. RELEASE (The Version - v1.0)
class Release(models.Model):
    """
    Represents a specific version of a Product (e.g. v1.2.0).
    Logic: 1 Release has 1 SBOM file.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='releases')
    
    name = models.CharField(max_length=100) # e.g. "v1.2.0"
    commit_hash = models.CharField(max_length=64, blank=True) # Git SHA
    
    # The Raw SBOM File (Evidence)
    sbom_file = models.FileField(upload_to='sboms/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'name') # Prevent duplicate v1.0.0

    def __str__(self):
        return f"{self.product.name} @ {self.name}"


class Component(models.Model):
    """
    The ingredients extracted from the SBOM.
    Used for searching: "Where is log4j used?"
    """
    COMPONENT_TYPES = [
        ('LIBRARY', 'Library'),
        ('FRAMEWORK', 'Framework'),
        ('CONTAINER', 'Container'),
        ('OS', 'Operating System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='components')
    
    name = models.CharField(max_length=200)       # e.g. "requests"
    version = models.CharField(max_length=100)    # e.g. "2.28.1"
    type = models.CharField(max_length=20, choices=COMPONENT_TYPES, default='LIBRARY')
    
    # PURL (Package URL) - The industry standard ID
    purl = models.CharField(max_length=300, blank=True) 
    license = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version}"

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

    # --- THREAT INTEL FIELDS ---
    # EPSS (0.0 to 1.0)
    epss_score = models.FloatField(default=0.0, db_index=True)
    epss_percentile = models.FloatField(default=0.0)

    # KEV (CISA)
    kev_status = models.BooleanField(default=False, db_index=True) # True if exploited
    kev_date = models.DateField(null=True, blank=True) # Date added to catalog

    # Metadata
    last_enrichment = models.DateTimeField(null=True, blank=True)

    # 1. STATUS MANAGEMENT
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('FIXED', 'Fixed'),
        ('FALSE_POSITIVE', 'False Positive'),
        ('RISK_ACCEPTED', 'Risk Accepted'),
        ('DUPLICATE', 'Duplicate'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', db_index=True)
    
    # 2. TRIAGE NOTES
    triage_note = models.TextField(blank=True, help_text="Reason for FP or Risk Acceptance")
    triage_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    triage_at = models.DateTimeField(null=True, blank=True)

    # 3. FINGERPRINTING (The secret sauce)
    # Allows us to track the *same* issue across multiple scans of the same release
    hash_id = models.CharField(max_length=64, db_index=True, editable=False)
    
    # 4. LIFECYCLE
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Generate deterministic hash
        unique_str = f"{self.cve_id}-{self.package_name}-{self.package_version}-{self.scan.release.id}"
        self.hash_id = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cve_id} in {self.package_name}"