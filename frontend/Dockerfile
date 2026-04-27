# View/Clip frontend — multi-stage: node build → nginx serve
FROM node:20-alpine AS build
WORKDIR /app
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY package.json yarn.lock ./
RUN yarn install

COPY . .
RUN yarn build

FROM nginx:alpine
# SPA fallback — any unknown route serves index.html so React Router handles it
RUN printf 'server {\n\
  listen 80;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / { try_files $uri /index.html; }\n\
  location /api { return 404; }\n\
}\n' > /etc/nginx/conf.d/default.conf

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
