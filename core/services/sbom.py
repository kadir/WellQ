import json
from core.models import Component
from core.utils.security import safe_json_load

def digest_sbom(release):
    """
    Reads release.sbom_file and populates the Component table.
    Tracks changes: NEW components, REMOVED components, and UNCHANGED components.
    """
    if not release.sbom_file:
        return

    try:
        # Security: Use safe JSON loading with size limits (max 50MB for SBOM)
        data = safe_json_load(release.sbom_file, max_size_mb=50)
        items = data.get('components', [])
        
        # Get existing components (using purl as unique identifier, fallback to name+version)
        # Only get components that are not marked as REMOVED (active components)
        existing_components = Component.objects.filter(release=release).exclude(status='REMOVED')
        existing_map = {}
        for comp in existing_components:
            # Use purl if available, otherwise use name+version as key
            key = comp.purl if comp.purl else f"{comp.name}@{comp.version}"
            existing_map[key] = comp
        
        # Process new SBOM components
        new_components_map = {}
        batch_create = []
        batch_update = []
        
        for item in items:
            c_type = item.get('type', 'library').upper()
            
            # Extract License safely
            license_id = "Unknown"
            if 'licenses' in item and item['licenses']:
                try:
                    license_id = item['licenses'][0]['license']['id']
                except:
                    pass

            name = item.get('name', 'unknown')
            version = item.get('version', '0.0.0')
            purl = item.get('purl', '')
            
            # Use purl if available, otherwise use name+version as key
            key = purl if purl else f"{name}@{version}"
            new_components_map[key] = {
                'name': name,
                'version': version,
                'type': c_type if c_type in ['LIBRARY', 'FRAMEWORK', 'CONTAINER'] else 'LIBRARY',
                'purl': purl,
                'license': license_id
            }
            
            # Check if component already exists
            if key in existing_map:
                # Component exists - mark as unchanged
                existing_comp = existing_map[key]
                existing_comp.status = 'UNCHANGED'
                batch_update.append(existing_comp)
            else:
                # New component
                comp = Component(
                    release=release,
                    name=name,
                    version=version,
                    type=c_type if c_type in ['LIBRARY', 'FRAMEWORK', 'CONTAINER'] else 'LIBRARY',
                    purl=purl,
                    license=license_id,
                    status='NEW'
                )
                batch_create.append(comp)
        
        # Mark removed components (exist in old SBOM but not in new)
        removed_keys = set(existing_map.keys()) - set(new_components_map.keys())
        for key in removed_keys:
            removed_comp = existing_map[key]
            removed_comp.status = 'REMOVED'
            batch_update.append(removed_comp)
        
        # Bulk operations
        if batch_create:
            Component.objects.bulk_create(batch_create)
        if batch_update:
            Component.objects.bulk_update(batch_update, ['status'])
        
        print(f"Digested {len(batch_create)} new, {len([c for c in batch_update if c.status == 'UNCHANGED'])} unchanged, {len(removed_keys)} removed components for {release.name}")

    except Exception as e:
        print(f"SBOM Parsing Error: {e}")