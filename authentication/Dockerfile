# Use an official Python runtime as a base image
FROM ubuntu:22.04

# Install necessary packages
RUN apt-get update && apt-get install -y python3-pip 

# Set the working directory in the container
WORKDIR /authentication

# Copy requirements.txt into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . /authentication

# Expose the port that the Strawberry app will run on
EXPOSE 5000

# Run the Strawberry app using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
