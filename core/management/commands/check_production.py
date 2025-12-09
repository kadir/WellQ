"""
Django management command to check production readiness.
Run this before deploying to production.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import sys
import os


class Command(BaseCommand):
    help = 'Check if the application is ready for production deployment'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Running production readiness checks...\n'))
        
        errors = []
        warnings = []
        
        # Check DEBUG mode
        if settings.DEBUG:
            errors.append("❌ DEBUG is True. Set DEBUG=False for production.")
        else:
            self.stdout.write(self.style.SUCCESS("✓ DEBUG is False"))
        
        # Check SECRET_KEY
        if settings.SECRET_KEY == 'default-insecure-key-for-dev':
            errors.append("❌ SECRET_KEY is using default value. Set a secure SECRET_KEY.")
        else:
            self.stdout.write(self.style.SUCCESS("✓ SECRET_KEY is set"))
        
        # Check ALLOWED_HOSTS
        if not settings.ALLOWED_HOSTS:
            errors.append("❌ ALLOWED_HOSTS is empty. Set ALLOWED_HOSTS for production.")
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ ALLOWED_HOSTS is set: {', '.join(settings.ALLOWED_HOSTS)}"))
        
        # Check database
        db_engine = os.getenv('DB_ENGINE', 'sqlite3').lower()
        if db_engine == 'sqlite3':
            warnings.append("⚠ Using SQLite database. Consider PostgreSQL for production.")
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Using {db_engine.upper()} database"))
        
        # Check static files
        if not settings.STATIC_ROOT:
            warnings.append("⚠ STATIC_ROOT is not set. Static files may not be served correctly.")
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ STATIC_ROOT is set: {settings.STATIC_ROOT}"))
        
        # Check security settings in production
        if not settings.DEBUG:
            if not settings.SESSION_COOKIE_SECURE:
                warnings.append("⚠ SESSION_COOKIE_SECURE is False. Enable for HTTPS.")
            else:
                self.stdout.write(self.style.SUCCESS("✓ SESSION_COOKIE_SECURE is enabled"))
            
            if not settings.CSRF_COOKIE_SECURE:
                warnings.append("⚠ CSRF_COOKIE_SECURE is False. Enable for HTTPS.")
            else:
                self.stdout.write(self.style.SUCCESS("✓ CSRF_COOKIE_SECURE is enabled"))
        
        # Run Django system checks
        self.stdout.write("\nRunning Django system checks...")
        try:
            call_command('check', '--deploy', verbosity=0)
            self.stdout.write(self.style.SUCCESS("✓ Django system checks passed"))
        except SystemExit:
            errors.append("❌ Django system checks failed. Run 'python manage.py check --deploy' for details.")
        
        # Summary
        self.stdout.write("\n" + "="*50)
        if errors:
            self.stdout.write(self.style.ERROR(f"\n❌ Found {len(errors)} error(s):"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  {error}"))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f"\n⚠ Found {len(warnings)} warning(s):"))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f"  {warning}"))
        
        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS("\n✓ All production checks passed!"))
            return
        
        if errors:
            self.stdout.write(self.style.ERROR("\n❌ Production deployment is NOT recommended. Fix errors above."))
            sys.exit(1)
        else:
            self.stdout.write(self.style.WARNING("\n⚠ Production deployment is possible but review warnings above."))






