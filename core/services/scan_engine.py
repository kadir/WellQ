from core.scanners import get_scanner

def process_scan_upload(scan, json_file):
    """
    Orchestrator:
    1. Finds the correct scanner tool.
    2. Runs the parser (which handles deduplication & updates).
    3. Returns the count of findings.
    """
    parser = get_scanner(scan.scanner_name)
    if parser:
        return parser.parse(scan, json_file)
    return 0