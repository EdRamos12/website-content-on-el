# syntax=docker/dockerfile:1
# Use official Python image as base
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip3 install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Run the Flask app
CMD [ "python3", "app.py"]