# Migration Fix Instructions

The migration for `risk_accepted_expires_at` field failed because the Finding model doesn't exist in the migration state yet.

## Solution

You need to generate the migrations properly. Run this command in your Docker container:

```bash
# Option 1: If you're using docker-compose
docker-compose exec web python manage.py makemigrations

# Option 2: If you're using docker-compose.simple.yml
docker-compose -f docker-compose.simple.yml exec web python manage.py makemigrations

# Then run migrations
docker-compose exec web python manage.py migrate
# OR
docker-compose -f docker-compose.simple.yml exec web python manage.py migrate
```

This will:
1. Create all initial migrations (if they don't exist)
2. Create the migration for `risk_accepted_expires_at` with correct dependencies
3. Apply all migrations

## Alternative: Manual Fix

If you want to fix it manually, you can:

1. Enter the Docker container:
```bash
docker-compose exec web bash
```

2. Run makemigrations:
```bash
python manage.py makemigrations core --name add_risk_accepted_expires_at
```

3. Run migrate:
```bash
python manage.py migrate
```

The `makemigrations` command will automatically detect the model change and create a migration with the correct dependencies.



