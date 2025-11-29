# Use a lightweight Node.js image
FROM node:alpine

# Set the working directory inside the container
WORKDIR /app

# Copy all project files to the container
COPY . .

# Install http-server globally
RUN npm install -g http-server

# Expose the port we want to run on (e.g., 8080)
EXPOSE 8080

# Start the server
# -p 8080: Listen on port 8080
# --proxy http://backend:8000?: This forwards any 404s (like /api/...) to your backend
# The '?' at the end is a catch-all query string placeholder required by some versions, 
# but usually just http://backend:8000 works too. 
CMD ["http-server", ".", "-p", "8080", "--proxy", "http://api:8000"]