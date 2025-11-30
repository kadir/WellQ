# Kubernetes Deployment Guide for WellQ

This guide explains how to deploy WellQ on Kubernetes using Helm charts, with specific instructions for Rancher.

## Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.0+
- kubectl configured
- Rancher access (optional)
- Docker image built and pushed to registry

## Quick Start

### 1. Build and Push Docker Image

```bash
# Build image
docker build -t your-registry/wellq:latest .

# Push to registry
docker push your-registry/wellq:latest
```

### 2. Install Helm Chart

```bash
# Navigate to helm chart
cd helm/wellq

# Update dependencies
helm dependency update

# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

# Install
helm install wellq . \
  --namespace wellq \
  --create-namespace \
  --set image.repository=your-registry/wellq \
  --set image.tag=latest \
  --set secrets.secretKey="$SECRET_KEY" \
  --set ingress.hosts[0].host=wellq.yourdomain.com \
  --set django.allowedHosts=wellq.yourdomain.com
```

## Rancher Deployment

### Method 1: Via Rancher UI

1. **Access Rancher UI**
   - Login to your Rancher instance
   - Select your cluster

2. **Navigate to Apps & Marketplace**
   - Click "Apps & Marketplace" in the left menu
   - Click "Manage" or "Launch"

3. **Deploy Helm Chart**
   - Select "Helm Chart"
   - Choose "Upload" or "Git Repository"
   - Upload the `helm/wellq` directory
   - Configure values (see Configuration section)
   - Click "Install"

### Method 2: Via Rancher CLI

```bash
# Install Rancher CLI (if not installed)
# Download from: https://github.com/rancher/cli/releases

# Login to Rancher
rancher login https://your-rancher-url/v3 \
  --token your-rancher-token

# Deploy app
rancher apps install wellq \
  --repo https://your-chart-repo \
  --namespace wellq \
  --set secrets.secretKey="$SECRET_KEY"
```

### Method 3: Via kubectl (Rancher-managed cluster)

```bash
# Ensure kubectl is configured for Rancher cluster
kubectl config use-context your-rancher-context

# Install Helm chart
helm install wellq ./helm/wellq \
  --namespace wellq \
  --create-namespace
```

## Configuration

### Create values.yaml

```yaml
# values.yaml
image:
  repository: your-registry/wellq
  tag: latest
  pullPolicy: IfNotPresent

django:
  secretKey: "your-secret-key-here"
  debug: "False"
  environment: "production"
  allowedHosts: "wellq.yourdomain.com"

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: wellq.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: wellq-tls
      hosts:
        - wellq.yourdomain.com

replicaCount:
  web: 3
  celery: 4
  celeryBeat: 1

resources:
  web:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

postgresql:
  enabled: true
  auth:
    database: "wellq"
    username: "wellq"
    password: "your-db-password"
  persistence:
    enabled: true
    size: 100Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: "your-redis-password"
  master:
    persistence:
      enabled: true
      size: 20Gi

storage:
  staticFiles:
    enabled: true
    size: 10Gi
  media:
    enabled: true
    size: 100Gi
```

### Install with Custom Values

```bash
helm install wellq ./helm/wellq \
  --namespace wellq \
  --create-namespace \
  -f values.yaml
```

## Post-Deployment Steps

### 1. Create Superuser

```bash
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py createsuperuser
```

### 2. Verify Deployment

```bash
# Check pods
kubectl get pods -n wellq

# Check services
kubectl get svc -n wellq

# Check ingress
kubectl get ingress -n wellq

# Check logs
kubectl logs -f deployment/wellq-web -n wellq
```

### 3. Access Application

- Web UI: https://wellq.yourdomain.com
- Admin: https://wellq.yourdomain.com/admin
- API Docs: https://wellq.yourdomain.com/api/swagger/

## Health Checks

Add health check endpoint to Django:

```python
# In core/urls.py
from django.http import HttpResponse

urlpatterns = [
    # ... other patterns
    path('health/', lambda r: HttpResponse('OK'), name='health'),
]
```

## Scaling

### Manual Scaling

```bash
# Scale web replicas
kubectl scale deployment wellq-web -n wellq --replicas=5

# Scale celery workers
kubectl scale deployment wellq-celery -n wellq --replicas=10
```

### Autoscaling (HPA)

Enable in values.yaml:

```yaml
autoscaling:
  web:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80
```

## Monitoring

### View Logs

```bash
# Web logs
kubectl logs -f deployment/wellq-web -n wellq

# Celery logs
kubectl logs -f deployment/wellq-celery -n wellq

# All pods
kubectl logs -f -l app.kubernetes.io/name=wellq -n wellq
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n wellq

# Node resource usage
kubectl top nodes
```

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n wellq

# Check events
kubectl get events -n wellq --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n wellq
```

### Database Issues

```bash
# Test connection
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py dbshell

# Check PostgreSQL pod
kubectl logs -f statefulset/wellq-postgresql -n wellq
```

### Redis Issues

```bash
# Test Redis
kubectl exec -it deployment/wellq-web -n wellq -- \
  python -c "import redis; r = redis.Redis.from_url('redis://...'); print(r.ping())"
```

### Persistent Volume Issues

```bash
# Check PVCs
kubectl get pvc -n wellq

# Check PVs
kubectl get pv

# Describe PVC
kubectl describe pvc wellq-media -n wellq
```

## Backup and Restore

### Database Backup

```bash
# Backup PostgreSQL
kubectl exec -it statefulset/wellq-postgresql -n wellq -- \
  pg_dump -U wellq wellq > backup.sql
```

### Restore Database

```bash
# Restore PostgreSQL
kubectl exec -i statefulset/wellq-postgresql -n wellq -- \
  psql -U wellq wellq < backup.sql
```

## Upgrades

```bash
# Upgrade Helm release
helm upgrade wellq ./helm/wellq \
  --namespace wellq \
  -f values.yaml

# Rollback if needed
helm rollback wellq --namespace wellq
```

## Uninstallation

```bash
# Uninstall Helm release
helm uninstall wellq --namespace wellq

# Delete namespace (optional)
kubectl delete namespace wellq
```

## Production Checklist

- [ ] Use external secrets management
- [ ] Enable autoscaling
- [ ] Use external managed database
- [ ] Configure proper resource limits
- [ ] Enable monitoring and alerting
- [ ] Set up database backups
- [ ] Configure TLS certificates
- [ ] Use CDN for static files
- [ ] Enable pod disruption budgets
- [ ] Configure network policies
- [ ] Set up log aggregation
- [ ] Configure health checks
- [ ] Test disaster recovery

## Additional Resources

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Rancher Documentation](https://rancher.com/docs/)



