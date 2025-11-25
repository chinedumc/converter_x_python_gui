FROM node:20-slim

# Set work directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install --production

# Copy the rest of the backend code
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads

# Expose port
EXPOSE 8000

# Set environment variables
ENV NODE_ENV=production

# Start the server
CMD ["node", "server.js"]