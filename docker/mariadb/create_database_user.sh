#!/bin/bash

# Ensure required environment variables are set
if [[ -z "$MARIADB_ROOT_PASSWORD" ||
      -z "$DJANGO_DB_NAME" ||
      -z "$DJANGO_DB_USER_NAME" ||
      -z "$DJANGO_DB_USER_PASSWORD" ]]; then
  echo "Required environment variables are missing."
  exit 1
fi

# Retry logic for MariaDB connection
until mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 -e "quit"; do
  echo "Error connecting to MariaDB, retrying..."
  sleep 5
done

echo "Successfully connected to MariaDB"

# Create database
echo "Creating database..."
mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 \
  -e "CREATE DATABASE IF NOT EXISTS \`$DJANGO_DB_NAME\` CHARACTER SET utf8mb4;"

# Create Django user
echo "Creating Django user..."
mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 \
  -e "CREATE USER IF NOT EXISTS \`$DJANGO_DB_USER_NAME\` IDENTIFIED BY '$DJANGO_DB_USER_PASSWORD';"

# Grant user rights on Django database
echo "Granting user rights on Django database..."
mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 \
  -e "GRANT ALL PRIVILEGES ON \`$DJANGO_DB_NAME\`.* TO \`$DJANGO_DB_USER_NAME\`;"

# Grant rights for running Django tests
echo "Granting rights for running Django tests..."
mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 \
  -e "GRANT CREATE ON *.* TO \`$DJANGO_DB_USER_NAME\`;"

# Grant rights on test database
echo "Granting rights on test database..."
mariadb -u root -p"$MARIADB_ROOT_PASSWORD" -h localhost -P 3306 \
  -e "GRANT ALL PRIVILEGES ON \`test_$DJANGO_DB_NAME\`.* TO \`$DJANGO_DB_USER_NAME\`;"

echo "Script completed successfully."
