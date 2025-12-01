# Dashboard Metrics & Visualizations - WellQ ASPM

## Recommended Dashboard Metrics

### 1. **Vulnerability Overview Cards** (Top Row)
- **Total Active Vulnerabilities** - Count of all ACTIVE findings
- **Critical/High Severity** - Count of CRITICAL + HIGH active findings
- **KEV (Exploited)** - Count of findings with kev_status=True
- **High EPSS Score** - Count of findings with EPSS > 0.7
- **Fix Rate** - Percentage of findings fixed in last 30 days
- **Risk Accepted** - Count of RISK_ACCEPTED findings

### 2. **Vulnerability Trends Over Time** (Line Chart)
- **X-axis**: Date (last 30/60/90 days)
- **Y-axis**: Count of vulnerabilities
- **Lines**: 
  - New vulnerabilities discovered
  - Fixed vulnerabilities
  - Active vulnerabilities (cumulative)
- **Purpose**: Track security posture improvement over time

### 3. **Severity Distribution** (Pie/Donut Chart)
- **Slices**: CRITICAL, HIGH, MEDIUM, LOW, INFO
- **Color coding**: Red (Critical) → Yellow (Info)
- **Purpose**: Quick visual of risk distribution

### 4. **Status Distribution** (Bar Chart)
- **Bars**: ACTIVE, FIXED, FALSE_POSITIVE, RISK_ACCEPTED, DUPLICATE
- **Purpose**: Understand triage status and workload

### 5. **Top 10 CVEs by Count** (Horizontal Bar Chart)
- **X-axis**: Count of occurrences
- **Y-axis**: CVE IDs
- **Color**: Based on severity
- **Purpose**: Identify most common vulnerabilities

### 6. **EPSS Score Distribution** (Histogram/Bar Chart)
- **Bins**: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
- **Purpose**: Understand exploitability risk

### 7. **KEV vs Non-KEV** (Pie Chart)
- **Slices**: Exploited (KEV=True), Not Exploited (KEV=False)
- **Purpose**: Focus on actively exploited vulnerabilities

### 8. **Vulnerabilities by Product** (Bar Chart)
- **X-axis**: Product names
- **Y-axis**: Count of active vulnerabilities
- **Color**: Based on product criticality
- **Purpose**: Identify products needing attention

### 9. **Scanner Coverage** (Stacked Bar Chart)
- **X-axis**: Scanner names (Trivy, etc.)
- **Y-axis**: Count of findings
- **Stacked by**: Severity
- **Purpose**: Understand scanner effectiveness

### 10. **Fix Velocity** (Line Chart)
- **X-axis**: Weeks/Months
- **Y-axis**: Average days to fix
- **Grouped by**: Severity
- **Purpose**: Track remediation speed

### 11. **Component Inventory Stats** (Cards)
- **Total Components** - Count of all components
- **New Components** - Components added in last 30 days
- **Removed Components** - Components removed in last 30 days
- **Components with Vulnerabilities** - Components that have associated findings

### 12. **Recent Activity Timeline** (Timeline/List)
- **Events**: 
  - New scans uploaded
  - Vulnerabilities fixed
  - Risk acceptances
  - SBOM updates
- **Purpose**: Real-time activity feed

### 13. **Risk Score by Workspace** (Heatmap/Bar Chart)
- **X-axis**: Workspaces
- **Y-axis**: Risk score (calculated from severity + EPSS + KEV)
- **Purpose**: Compare security posture across teams

### 14. **Vulnerability Age** (Bar Chart)
- **Bins**: 0-7 days, 7-30 days, 30-90 days, 90+ days
- **Purpose**: Identify stale vulnerabilities

### 15. **Triage Activity** (Line Chart)
- **X-axis**: Date
- **Y-axis**: Count
- **Lines**: 
  - False Positives marked
  - Risk Acceptances
  - Triage actions per day
- **Purpose**: Track security team activity

## Implementation Priority

### Phase 1 (Essential - Implement First):
1. Vulnerability Overview Cards
2. Severity Distribution
3. Status Distribution
4. Top 10 CVEs
5. KEV vs Non-KEV

### Phase 2 (Important):
6. Vulnerability Trends Over Time
7. EPSS Score Distribution
8. Vulnerabilities by Product
9. Component Inventory Stats

### Phase 3 (Nice to Have):
10. Scanner Coverage
11. Fix Velocity
12. Recent Activity Timeline
13. Risk Score by Workspace
14. Vulnerability Age
15. Triage Activity

## Technology Recommendations

- **Chart.js** - Lightweight, easy to use, good for most charts
- **Chartist.js** - Simple and responsive
- **ApexCharts** - Modern, feature-rich (if budget allows)
- **D3.js** - For custom visualizations (more complex)

For this project, I recommend **Chart.js** as it's:
- Free and open-source
- Well-documented
- Easy to integrate
- Good performance
- Supports all chart types we need




