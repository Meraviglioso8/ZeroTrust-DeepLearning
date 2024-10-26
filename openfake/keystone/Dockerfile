# Use Ubuntu as the base image
FROM ubuntu:22.04

# Install required dependencies and Python 3.10
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3.10 \
    python3.10-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    build-essential \
    git \
    curl \
    postgresql-client \
    python3-venv \
    software-properties-common \
    jq \
    uuid-runtime \
    netcat

# Set Python 3.10.10 as the default Python version
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Clone the Keystone source code from OpenStack repository
RUN git clone https://opendev.org/openstack/keystone /opt/keystone

# Set working directory to Keystone
WORKDIR /opt/keystone

# Install Keystone dependencies
RUN pip3 install -r requirements.txt

# Install Keystone itself
RUN python3 setup.py install

# Install OpenStack Keystone-related Python packages
RUN pip3 install uwsgi keystoneauth1 keystonemiddleware python-keystoneclient psycopg2-binary

# Create keystone user and group
RUN groupadd --system keystone && useradd --system --home-dir /var/lib/keystone --shell /bin/false -g keystone keystone

# Copy Keystone configuration files
COPY keystone.conf /etc/keystone/keystone.conf
COPY keystone-uwsgi-public.ini /etc/keystone/keystone-uwsgi-public.ini
COPY keystone-uwsgi-admin.ini /etc/keystone/keystone-uwsgi-admin.ini
COPY bootstrap.sh /usr/local/bin/bootstrap.sh
COPY initial.sh /usr/local/bin/initial.sh
COPY combined_entrypoint.sh /usr/local/bin/combined_entrypoint.sh

# Set permissions for the bootstrap script
RUN chmod +x /usr/local/bin/bootstrap.sh
RUN chmod +x /usr/local/bin/initial.sh

# Set permissions for the combined entrypoint script
RUN chmod +x /usr/local/bin/combined_entrypoint.sh

# Expose Keystone API ports (public and admin)
EXPOSE 5000 35357

# Set entrypoint to the bootstrap script
ENTRYPOINT ["/usr/local/bin/combined_entrypoint.sh"]
