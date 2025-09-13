# Stage 1: Build the application
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# If you were building for production, you would run `npm run build` here

# Stage 2: Serve the application
FROM node:18-alpine
WORKDIR /app
COPY --from=build /app .
# Expose Vite's default port
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
