FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./

ENV NODE_ENV=development
ENV HUSKY=0

RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]