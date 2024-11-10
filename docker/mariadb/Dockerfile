FROM quay.io/mariadb-foundation/mariadb-devel:11.6-vector-preview

# Clean up repo config file that points to no-longer existing repo
COPY ./docker/mariadb/create_database_user.sh \
     /docker-entrypoint-initdb.d/create_database_user.sh
RUN chmod +x /docker-entrypoint-initdb.d/create_database_user.sh
