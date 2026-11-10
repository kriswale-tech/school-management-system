FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./

ENV NODE_ENV=development

RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

EXPOSE 5174

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]
