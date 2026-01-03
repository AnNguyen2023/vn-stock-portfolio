FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build ứng dụng Next.js
RUN npm run build

# Chạy Next.js
CMD ["npm", "start"]