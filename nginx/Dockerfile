# Base Nginx image
FROM nginx:alpine

# Remove default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration
COPY default.conf /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Install git, Node.js, pnpm, and certbot
# npm은 nodejs 설치 시 함께 설치될 수 있지만, pnpm을 명시적으로 설치하고 사용합니다.
RUN apk add --no-cache git nodejs pnpm certbot certbot-nginx

# Create workspace directory for React app
RUN mkdir -p /workspace
# WORKDIR /workspace/app  # 클론할 때 생성되므로 app까지 지정할 필요 없음

# Clone the repository and specific branch
# RUN git clone --single-branch --branch dev_host https://github.com/hyeok8055/antd-pwa-mobile.git ./app
# RUN git clone --single-branch --branch dev_host https://github.com/hyeok8055/antd-pwa-mobile.git /workspace/app
# WORKDIR /workspace/app # 빌드 전에 작업 디렉토리 변경
# RUN npm install
# RUN npm run build # React 앱의 빌드 결과물은 dist 폴더에 생성된다고 가정. default.conf에서 root /workspace/dist; 로 되어 있으므로, 빌드 결과물을 /workspace/dist로 옮기거나, clone 경로를 /workspace로 하고 빌드 후 dist 폴더를 사용하도록 함.

# Clone repository into /workspace/frontend
RUN git clone --single-branch --branch dev_host https://github.com/hyeok8055/antd-pwa-mobile.git /workspace/frontend

# Set working directory to the cloned app
WORKDIR /workspace/frontend

# Install dependencies and build the React app using pnpm
RUN pnpm install
# RUN pnpm build
# The build output is typically in a 'dist' or 'build' folder.
# Assuming the build output is in 'build' and nginx root is /workspace/dist as per default.conf
# We need to ensure the content of /workspace/frontend/build (or dist) is available at /workspace/dist for nginx
# If default.conf root is /workspace/dist and react build output is /workspace/frontend/dist, then we need to adjust.
# Based on default.conf: root /workspace/dist;
# Let's assume the react app builds into a 'dist' folder. So a /workspace/frontend/dist will be created.
# We'll copy the content of /workspace/frontend/dist to /workspace/dist
RUN mkdir -p /workspace/dist && cp -r /workspace/frontend/dist/* /workspace/dist/ || cp -r /workspace/frontend/build/* /workspace/dist/

# Expose port 80 for Nginx
EXPOSE 80
# EXPOSE 443 # SSL 사용 시

# Start Nginx
CMD ["nginx", "-g", "daemon off;"] 