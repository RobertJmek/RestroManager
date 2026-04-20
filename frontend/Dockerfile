FROM node:20-alpine

WORKDIR /app

COPY frontend/package*.json ./frontend/

WORKDIR /app/frontend

RUN npm install

COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
