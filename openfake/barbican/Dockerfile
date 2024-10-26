# Use Ubuntu as the base image
FROM ubuntu:20.04

# Install required packages and dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    build-essential \
    git \
    python3-venv \
    libcurl4-openssl-dev \
    && apt-get clean

# Install uWSGI
RUN pip3 install uwsgi

# Clone Barbican source code from the OpenStack repository
RUN git clone https://opendev.org/openstack/barbican.git /opt/barbican

# Set the working directory to Barbican source
WORKDIR /opt/barbican

# Install Python dependencies
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r requirements.txt

# Install Barbican
RUN python3 setup.py install

# Create a user to run Barbican
RUN useradd -ms /bin/bash barbican

# Switch to the barbican user
USER barbican

# Expose the default Barbican API port
EXPOSE 9311

# Run the Barbican API server using uWSGI
CMD ["uwsgi", "--http", "0.0.0.0:9311", "--wsgi-file", "/opt/barbican/barbican/api/app.py", "--callable", "create_main_app", "--master", "--processes", "4", "--threads", "2"]

