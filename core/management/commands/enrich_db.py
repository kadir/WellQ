import gzip
import csv
import json
import requests
import io
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Finding, PlatformSettings

# Get URLs from settings
def get_epss_url():
    """Get EPSS URL from platform settings"""
    try:
        settings = PlatformSettings.get_settings()
        return settings.epss_url
    except:
        return "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"

def get_kev_url():
    """Get KEV URL from platform settings"""
    try:
        settings = PlatformSettings.get_settings()
        return settings.kev_url
    except:
        return "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

class Command(BaseCommand):
    help = 'Downloads EPSS/KEV databases and updates all findings'

    def handle(self, *args, **kwargs):
        epss_url = get_epss_url()
        kev_url = get_kev_url()
        
        self.stdout.write(f"Using EPSS URL: {epss_url}")
        self.stdout.write(f"Using KEV URL: {kev_url}")
        
        self.stdout.write("1. Downloading & Parsing KEV (CISA)...")
        kev_dict = self.fetch_kev(kev_url)
        
        self.stdout.write("2. Downloading & Parsing EPSS (First.org)...")
        epss_dict = self.fetch_epss(epss_url)

        self.stdout.write("3. Updating Findings (Batch Process)...")
        self.update_findings(kev_dict, epss_dict)
        
        self.stdout.write(self.style.SUCCESS("Enrichment Complete!"))

    def fetch_kev(self, kev_url=None):
        """Returns dict: {'CVE-2023-1234': '2023-05-12'}"""
        if kev_url is None:
            kev_url = get_kev_url()
        try:
            r = requests.get(kev_url)
            data = r.json()
            kev_map = {}
            for vul in data.get('vulnerabilities', []):
                cve = vul.get('cveID')
                date_added = vul.get('dateAdded') # Format YYYY-MM-DD
                kev_map[cve] = date_added
            return kev_map
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch KEV: {e}"))
            return {}

    def fetch_epss(self, epss_url=None):
        """Returns dict: {'CVE-2023-1234': {'score': 0.9, 'percentile': 0.95}}"""
        if epss_url is None:
            epss_url = get_epss_url()
        try:
            r = requests.get(epss_url)
            # Decompress GZIP in memory
            with gzip.open(io.BytesIO(r.content), 'rt') as f:
                # Skip header comments (lines starting with #)
                # The actual CSV header is 'cve,epss,percentile'
                reader = csv.reader(filter(lambda row: row[0] != '#', f))
                next(reader) # Skip header row
                
                epss_map = {}
                for row in reader:
                    # row = [cve, epss_score, percentile]
                    if len(row) >= 3:
                        epss_map[row[0]] = {
                            'score': float(row[1]),
                            'p': float(row[2])
                        }
                return epss_map
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch EPSS: {e}"))
            return {}

    def update_findings(self, kev_dict, epss_dict):
        # We define fields to update to optimize the SQL query
        fields_to_update = ['epss_score', 'epss_percentile', 'kev_status', 'kev_date', 'last_enrichment']
        
        batch = []
        batch_size = 2000 # Update 2000 rows at a time
        now = timezone.now()

        # Iterator() is crucial for 100k rows to keep memory low
        queryset = Finding.objects.all().iterator()
        
        count = 0
        total_updates = 0

        for finding in queryset:
            cve = finding.vulnerability_id
            updated = False

            # 1. Check EPSS
            if cve in epss_dict:
                data = epss_dict[cve]
                # Store EPSS in metadata
                if not finding.metadata:
                    finding.metadata = {}
                finding.metadata['epss_score'] = data['score']
                finding.metadata['epss_percentile'] = data.get('p', 0.0)
                updated = True

            # 2. Check KEV
            if cve in kev_dict:
                # Store KEV in metadata
                if not finding.metadata:
                    finding.metadata = {}
                finding.metadata['kev_status'] = True
                finding.metadata['kev_date'] = kev_dict[cve]
                updated = True
            
            # If we have data, mark as enriched
            if updated:
                finding.last_enrichment = now
                batch.append(finding)
                count += 1

            # When batch is full, push to DB
            if len(batch) >= batch_size:
                Finding.objects.bulk_update(batch, fields_to_update)
                total_updates += len(batch)
                self.stdout.write(f"   ...updated {total_updates} findings")
                batch = [] # Reset

        # Final flush
        if batch:
            Finding.objects.bulk_update(batch, fields_to_update)
            total_updates += len(batch)