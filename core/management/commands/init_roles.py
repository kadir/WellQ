"""
Management command to initialize default roles with their permissions.
Run this after migrations: python manage.py init_roles
"""
from django.core.management.base import BaseCommand
from core.models import Role


class Command(BaseCommand):
    help = 'Initialize default roles with their permissions'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'ADMINISTRATOR',
                'description': 'Full system access. Can manage all resources and users.',
                'permissions': {
                    'can_manage_users': True,
                    'can_manage_workspaces': True,
                    'can_manage_products': True,
                    'can_upload_scans': True,
                    'can_upload_sbom': True,
                    'can_triage_findings': True,
                    'can_view_all': True,
                    'can_export_data': True,
                    'can_manage_roles': True,
                }
            },
            {
                'name': 'PRODUCT_OWNER',
                'description': 'Can manage products, upload scans/SBOMs, and triage findings.',
                'permissions': {
                    'can_manage_products': True,
                    'can_upload_scans': True,
                    'can_upload_sbom': True,
                    'can_triage_findings': True,
                    'can_export_data': True,
                }
            },
            {
                'name': 'DEVELOPER',
                'description': 'Can upload scans and SBOMs, view findings for assigned products.',
                'permissions': {
                    'can_upload_scans': True,
                    'can_upload_sbom': True,
                    'can_export_data': True,
                }
            },
            {
                'name': 'SERVICE_ACCOUNT',
                'description': 'For automated systems and CI/CD pipelines. Can upload scans and SBOMs.',
                'permissions': {
                    'can_upload_scans': True,
                    'can_upload_sbom': True,
                }
            },
            {
                'name': 'SECURITY_EXPERT',
                'description': 'Can view all findings, triage vulnerabilities, and export reports.',
                'permissions': {
                    'can_triage_findings': True,
                    'can_view_all': True,
                    'can_export_data': True,
                }
            },
            {
                'name': 'AUDITOR',
                'description': 'Read-only access to all data for compliance and audit purposes.',
                'permissions': {
                    'can_view_all': True,
                    'can_export_data': True,
                }
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'description': role_data['description'],
                    **role_data['permissions']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created role: {role.get_name_display()}'))
            else:
                # Update existing role
                for key, value in role_data['permissions'].items():
                    setattr(role, key, value)
                role.description = role_data['description']
                role.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated role: {role.get_name_display()}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Roles initialized: {created_count} created, {updated_count} updated'
        ))



