import json
from .models import Component

def digest_sbom(release):
    """
    Reads release.sbom_file and populates the Component table.
    """
    if not release.sbom_file:
        return

    try:
        # Reset file pointer to beginning
        release.sbom_file.seek(0)
        data = json.load(release.sbom_file)
        
        # CycloneDX standard uses a 'components' list
        items = data.get('components', [])
        
        batch = []
        for item in items:
            # Extract Data
            name = item.get('name', 'unknown')
            version = item.get('version', '0.0.0')
            purl = item.get('purl', '')
            c_type = item.get('type', 'library').upper()
            
            # Extract License (Safely)
            license_id = "Unknown"
            if 'licenses' in item and item['licenses']:
                try:
                    license_id = item['licenses'][0]['license']['id']
                except:
                    pass

            # Create Object (In Memory)
            comp = Component(
                release=release,
                name=name,
                version=version,
                type=c_type if c_type in ['LIBRARY', 'FRAMEWORK', 'CONTAINER'] else 'LIBRARY',
                purl=purl,
                license=license_id
            )
            batch.append(comp)

        # Bulk Insert for Speed
        Component.objects.bulk_create(batch)
        print(f"Digested {len(batch)} components for {release.name}")

    except Exception as e:
        print(f"SBOM Parsing Error: {e}")