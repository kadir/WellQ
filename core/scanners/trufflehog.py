import json
import hashlib
import re
from django.utils import timezone
from core.models import Finding
from core.utils.security import safe_json_load
from .base import BaseScanner

class TrufflehogScanner(BaseScanner):
    """
    Parser for Trufflehog secret scanner results.
    
    Trufflehog outputs JSON in one of these formats:
    1. Single JSON object
    2. Array of JSON objects
    
    Each finding contains:
    - branch: Git branch name
    - commit: Commit message
    - commitHash: Git commit hash
    - date: Detection date
    - diff: Git diff showing the secret
    - path: File path where secret was found
    - printDiff: Formatted diff
    - reason: Why it was flagged (e.g., "High Entropy")
    - stringsFound: Array of secret strings found
    
    Note: Creates a separate Finding for each secret string found in stringsFound array.
    """
    
    def parse(self, scan_instance, json_file):
        try:
            # Security: Use safe JSON loading with size limits (max 100MB for scan files)
            data = safe_json_load(json_file, max_size_mb=100)
            
            # Support both artifact-based (new BOM) and release-based (legacy) modes
            artifact = scan_instance.artifact
            release = scan_instance.release
            
            # Determine the scope for deduplication
            if artifact:
                # New BOM architecture: deduplicate within artifact
                dedup_scope = {'scan__artifact': artifact}
                scope_id = artifact.id
            elif release:
                # Legacy mode: deduplicate within release
                dedup_scope = {'scan__release': release}
                scope_id = release.id
            else:
                # Fallback: deduplicate within scan
                dedup_scope = {'scan': scan_instance}
                scope_id = scan_instance.id
            
            now = timezone.now()

            # Handle different input formats
            # Trufflehog can output:
            # 1. A single JSON object
            # 2. An array of JSON objects
            findings_data = []
            
            if isinstance(data, list):
                # Array of findings
                findings_data = data
            elif isinstance(data, dict):
                # Single finding object
                findings_data = [data]
            else:
                # Unexpected format - log and return
                print(f"Trufflehog: Unexpected data format: {type(data)}")
                return 0

            # 1. FETCH ALL EXISTING (Map: Hash -> ID)
            # We only need ID and Status to make decisions
            existing_map = {
                f.hash_id: f 
                for f in Finding.objects.filter(**dedup_scope)
            }
            
            seen_hashes = set()
            
            # Lists for Bulk Operations
            to_create = []
            to_update = []

            for finding_data in findings_data:
                # Extract data from Trufflehog finding
                path = finding_data.get('path', 'Unknown')
                reason = finding_data.get('reason', 'Secret detected')
                commit_hash = finding_data.get('commitHash', '')
                strings_found = finding_data.get('stringsFound', [])
                branch = finding_data.get('branch', '')
                commit_msg = finding_data.get('commit', '')
                diff = finding_data.get('diff', '')
                
                # Process each secret string found
                # If multiple secrets in one finding, create separate findings for each
                for secret_string in strings_found:
                    # Generate secret hash for deduplication (don't store full secret)
                    secret_hash = hashlib.sha256(secret_string.encode('utf-8')).hexdigest()
                    
                    # Generate unique hash for this finding
                    # Use path + secret_hash + scope_id for uniqueness
                    unique_str = f"{path}-{secret_hash}-{scope_id}"
                    finding_hash = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
                    seen_hashes.add(finding_hash)

                    if finding_hash in existing_map:
                        # EXISTS: Prepare for Update
                        obj = existing_map[finding_hash]
                        
                        # Only update if something changed (Performance tweak)
                        needs_save = False
                        
                        if obj.status == Finding.Status.FIXED:
                            obj.status = Finding.Status.OPEN  # Regression
                            needs_save = True
                        
                        # Always update metadata
                        obj.scan = scan_instance
                        obj.last_seen = now
                        
                        # Add to update list
                        to_update.append(obj)
                    else:
                        # NEW: Prepare for Create
                        # Truncate secret string for display (don't store full secret in title)
                        secret_preview = secret_string[:50] + "..." if len(secret_string) > 50 else secret_string
                        
                        # Build title
                        title = f"Secret detected in {path} - {reason}"
                        
                        # Build description
                        description_parts = [
                            f"Reason: {reason}",
                            f"File: {path}",
                            f"Branch: {branch}" if branch else "",
                            f"Commit: {commit_hash}" if commit_hash else "",
                            f"Commit Message: {commit_msg}" if commit_msg else "",
                            f"Secret Preview: {secret_preview}",
                        ]
                        description = "\n".join([p for p in description_parts if p])
                        
                        # Add diff if available (truncated to avoid huge descriptions)
                        if diff:
                            diff_preview = diff[:500] + "..." if len(diff) > 500 else diff
                            description += f"\n\nDiff Preview:\n{diff_preview}"
                        
                        # Secrets are typically CRITICAL severity
                        severity = Finding.Severity.CRITICAL
                        
                        # Extract line number from diff if possible (basic parsing)
                        line_number = 0
                        if diff:
                            # Try to extract line number from diff (e.g., "@@ -42,3 +42,3 @@")
                            import re
                            line_match = re.search(r'@@\s*-\d+,\d+\s*\+(\d+),', diff)
                            if line_match:
                                line_number = int(line_match.group(1))
                        
                        to_create.append(Finding(
                            scan=scan_instance,
                            title=title,
                            description=description,
                            severity=severity,
                            finding_type=Finding.Type.SECRET,
                            file_path=path,
                            line_number=line_number,
                            hash_id=finding_hash,
                            status=Finding.Status.OPEN,
                            metadata={
                                'secret_hash': secret_hash,
                                'secret_preview': secret_preview,
                                'reason': reason,
                                'branch': branch,
                                'commit_hash': commit_hash,
                                'commit_message': commit_msg,
                                'detector': 'Trufflehog',
                                'verification': 'Verified' if reason else 'Unverified',
                            }
                        ))

            # 2. BULK OPERATIONS (The Speed Boost)
            
            # A. Bulk Create (1 Query)
            if to_create:
                Finding.objects.bulk_create(to_create)
            
            # B. Bulk Update (1 Query)
            if to_update:
                Finding.objects.bulk_update(to_update, ['scan', 'last_seen', 'status'], batch_size=100)

            # 3. AUTO-CLOSE LOGIC (1 Query)
            all_known_hashes = set(existing_map.keys())
            missing_hashes = all_known_hashes - seen_hashes
            
            if missing_hashes:
                Finding.objects.filter(
                    **dedup_scope,
                    hash_id__in=missing_hashes
                ).exclude(status=Finding.Status.FIXED).update(  # Don't update if already fixed
                    status=Finding.Status.FIXED,
                    last_seen=now
                )

            # 4. Snapshot
            scan_instance.findings_count = len(seen_hashes)
            scan_instance.save()

            return len(seen_hashes)

        except Exception as e:
            print(f"Trufflehog Parser Error: {e}")
            import traceback
            traceback.print_exc()
            return 0

