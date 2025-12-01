#!/bin/bash
# Redeploy script for WellQ - ensures all changes are picked up

echo "🔄 Redeploying WellQ..."
echo ""

# Step 1: Rebuild the web container (no cache to ensure fresh build)
echo "📦 Step 1: Rebuilding web container (no cache)..."
docker-compose build --no-cache web

# Step 2: Stop and remove the web container
echo ""
echo "🛑 Step 2: Stopping web container..."
docker-compose stop web
docker-compose rm -f web

# Step 3: Start the web container
echo ""
echo "🚀 Step 3: Starting web container..."
docker-compose up -d web

# Step 4: Wait a moment for container to start
echo ""
echo "⏳ Step 4: Waiting for container to be ready..."
sleep 5

# Step 5: Run collectstatic (in case static files changed)
echo ""
echo "📁 Step 5: Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput || echo "⚠️  collectstatic had issues (may be OK)"

# Step 6: Show container status
echo ""
echo "✅ Step 6: Container status:"
docker-compose ps web

echo ""
echo "🎉 Redeployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Clear your browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)"
echo "   2. Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)"
echo "   3. Check logs: docker-compose logs -f web"
echo ""


