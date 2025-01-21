# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container (excluding .env via .dockerignore)
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask server port
EXPOSE 5000

# Set Flask-specific environment variables
ENV FLASK_APP=AnalyzeWatcherServer.app
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Default command to run the app
CMD ["flask", "run"]
