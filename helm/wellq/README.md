# WellQ Helm Chart

This Helm chart deploys the WellQ ASPM Platform on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- kubectl configured to access your cluster
- Rancher (optional, for management UI)

## Installation

### 1. Add Bitnami Helm Repository (for PostgreSQL and Redis)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2. Install Dependencies

```bash
cd helm/wellq
helm dependency update
```

### 3. Create Secrets

```bash
# Generate a secure SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

# Create Kubernetes secret
kubectl create secret generic wellq-secrets \
  --from-literal=secret-key="$SECRET_KEY" \
  --namespace=wellq
```

### 4. Install the Chart

```bash
# Install with default values
helm install wellq . \
  --namespace wellq \
  --create-namespace \
  --set secrets.secretKey="$SECRET_KEY" \
  --set ingress.hosts[0].host=wellq.yourdomain.com \
  --set django.allowedHosts=wellq.yourdomain.com
```

### 5. Upgrade Existing Installation

```bash
helm upgrade wellq . \
  --namespace wellq \
  --set secrets.secretKey="$SECRET_KEY"
```

## Configuration

### Key Configuration Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image repository | `wellq` |
| `image.tag` | Docker image tag | `latest` |
| `replicaCount.web` | Number of web replicas | `2` |
| `replicaCount.celery` | Number of Celery workers | `2` |
| `django.secretKey` | Django SECRET_KEY | Must be set |
| `django.allowedHosts` | ALLOWED_HOSTS | `wellq.example.com` |
| `ingress.enabled` | Enable Ingress | `true` |
| `ingress.hosts[0].host` | Ingress hostname | `wellq.example.com` |
| `postgresql.enabled` | Use Bitnami PostgreSQL | `true` |
| `redis.enabled` | Use Bitnami Redis | `true` |
| `storage.media.enabled` | Enable persistent storage for media | `true` |
| `storage.media.size` | Media storage size | `50Gi` |

### Example: Custom Values File

Create `my-values.yaml`:

```yaml
image:
  repository: your-registry/wellq
  tag: v1.0.0

django:
  secretKey: "your-secret-key"
  allowedHosts: "wellq.yourdomain.com"
  debug: "False"

ingress:
  enabled: true
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

resources:
  web:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

autoscaling:
  web:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    password: "your-db-password"
  persistence:
    size: 100Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: "your-redis-password"
```

Install with custom values:

```bash
helm install wellq . \
  --namespace wellq \
  --create-namespace \
  -f my-values.yaml
```

## Using External Database/Redis

### External PostgreSQL

```yaml
database:
  external:
    enabled: true
    host: "postgres.example.com"
    port: 5432
    name: "wellq"
    user: "wellq"
    password: "password"  # Set via secret

postgresql:
  enabled: false

secrets:
  dbPassword: "base64-encoded-password"
```

### External Redis

```yaml
redis:
  external:
    enabled: true
    host: "redis.example.com"
    port: 6379
    password: "password"  # Set via secret

redis:
  enabled: false

secrets:
  redisPassword: "base64-encoded-password"
```

## Rancher Deployment

### Via Rancher UI

1. Go to your cluster in Rancher
2. Navigate to Apps & Marketplace
3. Click "Manage" or "Launch"
4. Select "Helm Chart"
5. Upload the chart or use Git repository
6. Configure values
7. Deploy

### Via Rancher CLI

```bash
rancher apps install wellq \
  --repo https://your-chart-repo \
  --namespace wellq \
  --set secrets.secretKey="$SECRET_KEY"
```

## Post-Installation

### 1. Create Superuser

```bash
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py createsuperuser
```

### 2. Run Migrations (if needed)

```bash
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py migrate
```

### 3. Collect Static Files (if needed)

```bash
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py collectstatic --noinput
```

### 4. Check Pod Status

```bash
kubectl get pods -n wellq
```

### 5. Check Logs

```bash
# Web logs
kubectl logs -f deployment/wellq-web -n wellq

# Celery logs
kubectl logs -f deployment/wellq-celery -n wellq

# Celery Beat logs
kubectl logs -f deployment/wellq-celery-beat -n wellq
```

## Monitoring

### Health Checks

The chart includes health check endpoints. Ensure your Django app has:

```python
# In core/urls.py
urlpatterns = [
    # ... other patterns
    path('health/', lambda r: HttpResponse('OK'), name='health'),
]
```

### Metrics (Optional)

If Prometheus is installed:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n wellq

# Check logs
kubectl logs <pod-name> -n wellq

# Check events
kubectl get events -n wellq --sort-by='.lastTimestamp'
```

### Database Connection Issues

```bash
# Test database connection
kubectl exec -it deployment/wellq-web -n wellq -- \
  python manage.py dbshell
```

### Redis Connection Issues

```bash
# Test Redis connection
kubectl exec -it deployment/wellq-web -n wellq -- \
  python -c "import redis; r = redis.Redis.from_url('redis://...'); r.ping()"
```

### Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc -n wellq

# Check PV status
kubectl get pv
```

## Uninstallation

```bash
helm uninstall wellq --namespace wellq

# Delete namespace (optional)
kubectl delete namespace wellq
```

## Production Recommendations

1. **Use External Secrets**: Use External Secrets Operator or Sealed Secrets
2. **Enable Autoscaling**: Configure HPA based on your load
3. **Use External Database**: Use managed PostgreSQL service
4. **Enable Monitoring**: Set up Prometheus and Grafana
5. **Configure Backup**: Set up database backups
6. **Use CDN**: Serve static files via CDN
7. **Enable TLS**: Configure proper TLS certificates
8. **Resource Limits**: Set appropriate resource requests/limits
9. **Pod Disruption Budget**: Ensure high availability
10. **Network Policies**: Restrict network access

## Support

For issues and questions:
- Check logs: `kubectl logs -n wellq`
- Review Helm values: `helm get values wellq -n wellq`
- Check Rancher UI for cluster status






