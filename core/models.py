import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('REMOVED', 'Removed'),
        ('UNCHANGED', 'Unchanged'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='components')
    
    name = models.CharField(max_length=200)       # e.g. "requests"
    version = models.CharField(max_length=100)    # e.g. "2.28.1"
    type = models.CharField(max_length=20, choices=COMPONENT_TYPES, default='LIBRARY')
    
    # PURL (Package URL) - The industry standard ID
    purl = models.CharField(max_length=300, blank=True) 
    license = models.CharField(max_length=100, blank=True)
    
    # Change tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNCHANGED', db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version}"

# 4. SCAN (The Event)
class Scan(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='scans')
    
    scanner_name = models.CharField(max_length=50)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    findings_count = models.IntegerField(default=0)

# 5. FINDING (Polymorphic Storage - Generic Finding Table)
class Finding(models.Model):
    """
    Polymorphic Finding model using JSON sidecar pattern.
    
    Fixed Columns: Data every tool has (Severity, Title, Status, File Path)
    JSON Column (metadata): Data specific to the tool (CVE IDs, Hash strings, Line numbers)
    """
    
    # --- ENUMS ---
    class Severity(models.TextChoices):
        CRITICAL = 'CRITICAL', 'Critical'
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'
        INFO = 'INFO', 'Info'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        FIXED = 'FIXED', 'Fixed'
        WONT_FIX = 'WONT_FIX', 'Risk Accepted'
        FALSE_POSITIVE = 'FALSE_POSITIVE', 'False Positive'

    class Type(models.TextChoices):
        SCA = 'SCA', 'SCA (Libraries)'       # Trivy, Grype, JFrog Xray
        SECRET = 'SECRET', 'Secret'          # TruffleHog, Gitleaks
        SAST = 'SAST', 'SAST (Code)'         # SonarQube, Semgrep
        IAC = 'IAC', 'IaC (Config)'          # Checkov, tfsec
        CONTAINER = 'CONTAINER', 'Container' # OS Packages

    # --- CORE FIELDS ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name='findings')
    
    # Uniqueness Fingerprint (Generated by us)
    hash_id = models.CharField(max_length=64, db_index=True, editable=False)
    
    # 1. WHAT is it?
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # 2. HOW bad is it?
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    finding_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SCA)
    
    # 3. WHERE is it? (Generic Location)
    file_path = models.CharField(max_length=512, blank=True, null=True)  # e.g. /app/settings.py
    line_number = models.IntegerField(default=0)  # e.g. 42
    
    # 4. SCA Specifics (Optimized for filtering)
    # We keep these as columns because they are queried frequently
    vulnerability_id = models.CharField(max_length=50, blank=True, null=True, db_index=True)  # CVE-2024-1234, GHSA-xxxx, etc.
    package_name = models.CharField(max_length=255, blank=True, null=True)    # django
    package_version = models.CharField(max_length=100, blank=True, null=True)  # 4.2.1
    fix_version = models.CharField(max_length=100, blank=True, null=True)     # 4.2.2
    
    # 5. The "Catch-All" Bucket (JSON)
    # Stores: CVSS scores, EPSS, Secret Hashes, SAST Rule IDs, KEV status, etc.
    metadata = models.JSONField(default=dict, blank=True)
    
    # --- STATUS & LIFECYCLE ---
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(default=timezone.now)
    
    # --- TRIAGE NOTES (Workflow) ---
    triage_note = models.TextField(blank=True, help_text="Reason for FP or Risk Acceptance")
    triage_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    triage_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['hash_id']),
            models.Index(fields=['scan', 'status']),
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['finding_type', 'status']),
            models.Index(fields=['vulnerability_id']),
        ]
        ordering = ['-first_seen']

    def save(self, *args, **kwargs):
        # Generate deterministic hash based on finding type
        # This ensures proper deduplication across different scanner types
        # Only generate if hash_id is not already set (scanners set it explicitly)
        if not self.hash_id and self.scan and self.scan.release:
            if self.finding_type == Finding.Type.SECRET:
                # For secrets: use file_path + metadata secret hash + release.id
                secret_hash = (self.metadata or {}).get('secret_hash', '')
                unique_str = f"{self.file_path or ''}-{secret_hash}-{self.scan.release.id}"
            elif self.finding_type == Finding.Type.SCA:
                # For SCA: use vulnerability_id + package_name + package_version + release.id
                unique_str = f"{self.vulnerability_id or ''}-{self.package_name or ''}-{self.package_version or ''}-{self.scan.release.id}"
            else:
                # For SAST/IAC: use file_path + line_number + title + release.id
                unique_str = f"{self.file_path or ''}-{self.line_number}-{self.title}-{self.scan.release.id}"
            
            self.hash_id = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    # --- HELPER PROPERTIES (for backward compatibility with templates) ---
    @property
    def cve_id(self):
        """Backward compatibility: alias for vulnerability_id"""
        return self.vulnerability_id or ''
    
    @property
    def fixed_version(self):
        """Backward compatibility: alias for fix_version"""
        return self.fix_version or ''
    
    @property
    def epss_score(self):
        """Get EPSS score from metadata"""
        return (self.metadata or {}).get('epss_score', 0.0)
    
    @property
    def epss_percentile(self):
        """Get EPSS percentile from metadata"""
        return (self.metadata or {}).get('epss_percentile', 0.0)
    
    @property
    def kev_status(self):
        """Get KEV status from metadata"""
        return (self.metadata or {}).get('kev_status', False)
    
    @property
    def kev_date(self):
        """Get KEV date from metadata"""
        return (self.metadata or {}).get('kev_date', None)

    def __str__(self):
        return f"[{self.severity}] {self.title}"


# API Token Model for Secure API Authentication
class APIToken(models.Model):
    """
    Secure API tokens for authenticating API requests.
    Tokens can be created, viewed, and revoked by users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='api_tokens')
    
    name = models.CharField(
        max_length=100,
        help_text="A descriptive name for this token (e.g., 'CI/CD Pipeline', 'Monitoring Script')"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        help_text="The actual token value (hashed)"
    )
    token_preview = models.CharField(
        max_length=20,
        editable=False,
        help_text="First 8 characters of token for display"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def revoke(self):
        """Revoke this token"""
        self.is_active = False
        self.save()
    
    def is_expired(self):
        """Check if token is expired"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    def is_valid(self):
        """Check if token is valid (active and not expired)"""
        return self.is_active and not self.is_expired()


# Role Model for User Permissions
class Role(models.Model):
    """
    User roles for access control and permissions.
    """
    ROLE_CHOICES = [
        ('ADMINISTRATOR', 'Administrator'),
        ('PRODUCT_OWNER', 'Product Owner'),
        ('DEVELOPER', 'Developer'),
        ('SERVICE_ACCOUNT', 'Service Account'),
        ('SECURITY_EXPERT', 'Security Expert'),
        ('AUDITOR', 'Auditor'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True, help_text="Description of this role's permissions")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Permissions (can be extended later)
    can_manage_users = models.BooleanField(default=False, help_text="Can create, edit, and delete users")
    can_manage_workspaces = models.BooleanField(default=False, help_text="Can create, edit, and delete workspaces")
    can_manage_products = models.BooleanField(default=False, help_text="Can create, edit, and delete products")
    can_upload_scans = models.BooleanField(default=False, help_text="Can upload scan results")
    can_upload_sbom = models.BooleanField(default=False, help_text="Can upload SBOM files")
    can_triage_findings = models.BooleanField(default=False, help_text="Can change vulnerability status (FP, Risk Accepted, etc.)")
    can_view_all = models.BooleanField(default=False, help_text="Can view all workspaces and products")
    can_export_data = models.BooleanField(default=False, help_text="Can export SBOMs and reports")
    can_manage_roles = models.BooleanField(default=False, help_text="Can manage roles and permissions")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


# User Profile Extension (Many-to-Many relationship with Roles)
class UserProfile(models.Model):
    """
    Extended user profile with role assignments.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    roles = models.ManyToManyField(Role, blank=True, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} Profile"
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return self.roles.filter(name=role_name).exists()
    
    def has_permission(self, permission):
        """Check if user has a specific permission based on their roles"""
        return self.roles.filter(**{permission: True}).exists()
    
    def get_all_permissions(self):
        """Get all permissions for this user based on their roles"""
        permissions = {}
        for role in self.roles.all():
            permissions['can_manage_users'] = permissions.get('can_manage_users', False) or role.can_manage_users
            permissions['can_manage_workspaces'] = permissions.get('can_manage_workspaces', False) or role.can_manage_workspaces
            permissions['can_manage_products'] = permissions.get('can_manage_products', False) or role.can_manage_products
            permissions['can_upload_scans'] = permissions.get('can_upload_scans', False) or role.can_upload_scans
            permissions['can_upload_sbom'] = permissions.get('can_upload_sbom', False) or role.can_upload_sbom
            permissions['can_triage_findings'] = permissions.get('can_triage_findings', False) or role.can_triage_findings
            permissions['can_view_all'] = permissions.get('can_view_all', False) or role.can_view_all
            permissions['can_export_data'] = permissions.get('can_export_data', False) or role.can_export_data
            permissions['can_manage_roles'] = permissions.get('can_manage_roles', False) or role.can_manage_roles
        return permissions


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when a User is created"""
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception:
            # Ignore if table doesn't exist yet (migrations not run)
            pass


# Platform Settings Model
class PlatformSettings(models.Model):
    """
    Singleton model for platform-wide settings.
    Only one instance should exist.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # EPSS Configuration
    epss_url = models.URLField(
        default="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
        help_text="URL for EPSS scores CSV (gzipped)"
    )
    
    # KEV Configuration
    kev_url = models.URLField(
        default="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        help_text="URL for CISA KEV JSON feed"
    )
    
    def clean(self):
        """Validate URLs to prevent SSRF attacks"""
        from django.core.exceptions import ValidationError
        from urllib.parse import urlparse
        import ipaddress
        
        def validate_url(url, field_name):
            """Validate a single URL for SSRF protection"""
            if not url:
                return
            
            parsed = urlparse(url)
            
            # Only allow http and https schemes
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError({field_name: 'Only http and https URLs are allowed.'})
            
            # Require hostname
            if not parsed.hostname:
                raise ValidationError({field_name: 'URL must have a valid hostname.'})
            
            # Block private/internal IP addresses and localhost
            hostname = parsed.hostname.lower()
            
            # Check for localhost variations
            localhost_variants = ['localhost', '127.0.0.1', '0.0.0.0', '::1', 'localhost.localdomain']
            if hostname in localhost_variants:
                raise ValidationError({field_name: 'Localhost URLs are not allowed for security reasons.'})
            
            # Check for private IP ranges
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValidationError({field_name: 'Private/internal IP addresses are not allowed.'})
            except ValueError:
                # Not an IP address, check for private domain patterns
                if any(pattern in hostname for pattern in ['.local', '.internal', '.lan', '10.', '172.16.', '192.168.']):
                    raise ValidationError({field_name: 'Private/internal domains are not allowed.'})
            
            # Block file:// and other dangerous schemes in the path
            if '://' in parsed.path or parsed.path.startswith('//'):
                raise ValidationError({field_name: 'Invalid URL path detected.'})
        
        # Validate both URLs
        validate_url(self.epss_url, 'epss_url')
        validate_url(self.kev_url, 'kev_url')
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )
    
    class Meta:
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"
    
    def __str__(self):
        return "Platform Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings_obj = cls.objects.first()
        if not settings_obj:
            settings_obj = cls.objects.create(
                epss_url="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
                kev_url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
            )
        return settings_obj
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and PlatformSettings.objects.exists():
            # If settings already exist, update the existing one
            existing = PlatformSettings.objects.first()
            existing.epss_url = self.epss_url
            existing.kev_url = self.kev_url
            existing.updated_by = self.updated_by
            return existing.save(*args, **kwargs)
        return super().save(*args, **kwargs)


# Status Approval Request Model
class StatusApprovalRequest(models.Model):
    """
    Tracks requests to change vulnerability status that require approval.
    Only Security Expert and Administrator roles can approve these requests.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(Finding, on_delete=models.CASCADE, related_name='approval_requests')
    
    # Request details
    requested_status = models.CharField(max_length=30, choices=Finding.Status.choices)
    triage_note = models.TextField(blank=True, help_text="Reason for status change")
    requested_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='status_approval_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    # Approval details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    reviewed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_status_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, help_text="Optional note from reviewer")
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['finding', 'status']),
        ]
    
    def __str__(self):
        return f"Approval request for {self.finding.vulnerability_id or 'N/A'} - {self.requested_status} by {self.requested_by.username}"
    
    def approve(self, reviewer, review_note=''):
        """Approve this request and update the finding status"""
        from django.utils import timezone
        
        if self.status != 'PENDING':
            raise ValueError("Can only approve pending requests")
        
        # Update the finding
        self.finding.status = self.requested_status
        self.finding.triage_note = self.triage_note
        self.finding.triage_by = self.requested_by
        self.finding.triage_at = timezone.now()
        self.finding.save()
        
        # Update the approval request
        self.status = 'APPROVED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = review_note
        self.save()
    
    def reject(self, reviewer, review_note=''):
        """Reject this request"""
        from django.utils import timezone
        
        if self.status != 'PENDING':
            raise ValueError("Can only reject pending requests")
        
        self.status = 'REJECTED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = review_note
        self.save()