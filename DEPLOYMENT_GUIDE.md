# 프로젝트 배포 및 운영 가이드

이 문서는 제공된 Docker 기반 웹 애플리케이션 (Nginx + React Frontend + FastAPI Backend)을 Azure 클라우드 Ubuntu 인스턴스에 배포하고, 실행하며, 유지보수하는 전체 과정을 안내합니다.

## 1. 프로젝트 개요

본 프로젝트는 다음과 같은 주요 구성 요소로 이루어져 있습니다:

*   **Nginx (웹 서버 및 리버스 프록시)**:
    *   정적 웹 파일 (React 빌드 결과물)을 호스팅합니다.
    *   FastAPI 백엔드 API 요청을 위한 리버스 프록시 역할을 합니다.
    *   Certbot을 사용하여 SSL/TLS 인증서를 관리하고 HTTPS를 적용합니다.
*   **React Frontend**:
    *   사용자 인터페이스를 제공하는 웹 애플리케이션입니다.
    *   Nginx Docker 이미지 빌드 시 지정된 Git 리포지토리의 `dev_host` 브랜치에서 클론되어 빌드됩니다.
*   **FastAPI Backend**:
    *   Python 기반의 API 서버입니다.
    *   애플리케이션의 비즈니스 로직을 처리합니다.
*   **Docker & Docker Compose**:
    *   애플리케이션의 각 구성 요소를 컨테이너화하여 격리된 환경에서 실행합니다.
    *   `docker-compose.yml` 파일을 통해 다중 컨테이너 애플리케이션을 정의하고 관리합니다.

## 2. Azure 인스턴스 사전 준비 사항

Azure Ubuntu VM 인스턴스에 다음 소프트웨어가 설치되어 있어야 합니다:

1.  **Git**: 프로젝트 파일을 클론하거나 가져오기 위해 필요합니다.
    ```bash
    sudo apt update
    sudo apt install git -y
    ```
2.  **Docker**: 컨테이너를 실행하기 위한 필수 엔진입니다.
    ```bash
    sudo apt install docker.io -y
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER 
    # 변경사항 적용을 위해 로그아웃 후 다시 로그인하거나 새 쉘 세션을 시작하세요.
    ```
    (설치 후 새 쉘 세션을 시작하거나 재로그인하여 `sudo` 없이 `docker` 명령을 사용할 수 있도록 합니다.)
3.  **Docker Compose (v2)**: 다중 컨테이너 Docker 애플리케이션을 쉽게 관리하기 위해 필요합니다.
    ```bash
    sudo apt install docker-compose-v2 -y 
    # 또는 최신 버전 설치 방법은 공식 Docker 문서를 참조하세요.
    # 설치 후 'docker compose' 명령어로 사용합니다.
    ```
4.  **도메인 이름**: SSL 인증서 발급을 위해, Azure VM 인스턴스의 공인 IP 주소 (`20.39.191.188` 또는 할당된 IP)를 가리키는 유효한 도메인 이름이 필요합니다.
5.  **Azure 네트워크 보안 그룹 (NSG) / 방화벽**:
    *   **TCP 포트 80 (HTTP)**: Certbot 초기 인증 및 HTTP에서 HTTPS로의 리디렉션을 위해 열려 있어야 합니다.
    *   **TCP 포트 443 (HTTPS)**: 주 애플리케이션 서비스 및 SSL 통신을 위해 열려 있어야 합니다.

## 3. 프로젝트 배포

다음 방법 중 하나를 선택하여 프로젝트 파일을 Azure 인스턴스로 옮깁니다.

**방법 1: Git을 사용하여 프로젝트 클론 (권장)**

만약 이 프로젝트가 Git 리포지토리에 있다면, 해당 리포지토리를 클론합니다.

```bash
git clone <your-repository-url>
cd <project-directory-name>
```

**방법 2: 수동으로 파일 복사 (예: `scp`)**

로컬 머신에 프로젝트 파일들이 있다면 `scp` (Secure Copy)를 사용하여 Azure 인스턴스로 복사할 수 있습니다.

로컬 머신 터미널에서:
```bash
# 예시: 현재 디렉토리의 모든 내용을 Azure 인스턴스의 홈 디렉토리 아래 project_name 폴더로 복사
scp -r ./* your_username@your_azure_instance_ip:~/project_name/
```
이후 Azure 인스턴스에 SSH로 접속하여 해당 디렉토리로 이동합니다.
```bash
ssh your_username@your_azure_instance_ip
cd ~/project_name
```

프로젝트 파일 구조는 다음과 같아야 합니다:
```
project_root/
├── docker-compose.yml
├── fastapi/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── nginx/
│   ├── Dockerfile
│   ├── default.conf
│   └── nginx.conf
├── CERTBOT_GUIDE.md
└── DEPLOYMENT_GUIDE.md (현재 이 파일)
```

## 4. 초기 설정 및 구성

1.  **Nginx 설정 파일 수정 (`nginx/default.conf`)**:
    *   `nginx/default.conf` 파일을 열어 `server_name YOUR_DOMAIN_HERE;` 부분을 실제 **소유하고 있는 도메인 이름으로 변경**합니다. 이 도메인은 Azure VM의 공인 IP를 가리켜야 합니다.
    *   예: `server_name myapp.example.com;` 또는 `server_name myapp.example.com www.myapp.example.com;`
2.  **Frontend Git 리포지토리 확인 (필요시 `nginx/Dockerfile` 수정)**:
    *   `nginx/Dockerfile` 내부에 React Frontend를 클론하는 `git clone --single-branch --branch dev_host https://github.com/hyeok8055/antd-pwa-mobile.git /workspace/frontend` 부분이 있습니다.
    *   만약 다른 리포지토리나 브랜치를 사용해야 한다면 이 부분을 수정하십시오.

## 5. 애플리케이션 실행

프로젝트의 루트 디렉토리 (`docker-compose.yml` 파일이 있는 위치)에서 다음 명령을 실행하여 모든 서비스를 빌드하고 시작합니다:

```bash
docker compose up --build -d
```
*   `--build`: Docker 이미지를 강제로 다시 빌드합니다 (최초 실행 시 또는 Dockerfile 변경 시 필요).
*   `-d`: 컨테이너를 백그라운드에서 실행합니다.

몇 분 정도 소요될 수 있으며, 특히 Nginx 이미지는 React 앱을 클론하고 빌드하는 과정이 포함됩니다.

**실행 확인 (초기 HTTP):**
빌드가 완료되면, 설정한 도메인 (예: `http://YOUR_DOMAIN_HERE`)으로 접속하여 Nginx가 기본 페이지를 제공하는지 확인합니다. 이 단계에서는 아직 HTTPS가 설정되지 않았을 수 있습니다.

## 6. SSL 인증서 설정 (Certbot 사용)

웹사이트 보안을 위해 SSL/TLS 인증서를 설정해야 합니다. 본 프로젝트는 Nginx 컨테이너 내에서 Certbot을 사용하여 Let's Encrypt 인증서를 발급받고 관리하도록 구성되어 있습니다.

자세한 SSL 인증서 발급 및 자동 갱신 설정 과정은 함께 제공된 **`CERTBOT_GUIDE.md` 파일을 참조**하십시오. 이 가이드의 단계를 따르면 HTTPS가 활성화됩니다.

`CERTBOT_GUIDE.md`의 주요 단계 요약:
1.  Nginx 컨테이너에 접속합니다: `docker compose exec nginx sh`
2.  Certbot 명령을 실행하여 인증서를 발급받습니다 (도메인 및 이메일 주소 입력 필요).
3.  Nginx 설정을 리로드합니다.
4.  인증서 자동 갱신을 위한 cron 작업을 설정합니다.

## 7. 유지보수 및 관리

### 7.1. 로그 확인

*   **Nginx 로그**:
    ```bash
    docker compose logs nginx
    docker compose logs -f nginx # 실시간 로그 확인
    ```
    Nginx 컨테이너 내의 상세 로그는 `docker-compose.yml`에 설정된 볼륨 (`./nginx/logs`) 또는 컨테이너 내부 (`/var/log/nginx/`)에서 확인할 수 있습니다.
*   **FastAPI 로그**:
    ```bash
    docker compose logs fastapi
    docker compose logs -f fastapi # 실시간 로그 확인
    ```
    FastAPI 컨테이너 내의 상세 로그는 `docker-compose.yml`에 설정된 볼륨 (`./fastapi/logs`) 또는 컨테이너 내부 (`/app/logs/`)에서 확인할 수 있습니다.

### 7.2. 서비스 중지/시작/재시작

*   **모든 서비스 중지 (컨테이너 유지)**:
    ```bash
    docker compose stop
    ```
*   **모든 서비스 시작 (중지된 컨테이너)**:
    ```bash
    docker compose start
    ```
*   **모든 서비스 재시작**:
    ```bash
    docker compose restart
    ```
*   **모든 서비스 중지 및 컨테이너/네트워크 제거**:
    ```bash
    docker compose down
    ```
    (명명된 볼륨 `certbot_certs`, `certbot_lib` 등은 `docker compose down -v`를 사용해야 제거됩니다. 주의해서 사용하세요.)

### 7.3. 애플리케이션 업데이트

#### 7.3.1. Frontend 업데이트 (React App)

Nginx Dockerfile은 Git 리포지토리에서 Frontend 코드를 클론하여 빌드합니다. Frontend 코드가 해당 Git 리포지토리의 `dev_host` 브랜치에서 업데이트된 경우 다음 단계를 따릅니다.

1.  **Nginx 서비스 이미지 재빌드 및 재시작**:
    ```bash
    docker compose up --build -d nginx
    ```
    또는
    ```bash
    docker compose build nginx
    docker compose up -d --no-deps nginx 
    # --no-deps는 의존성 서비스(fastapi)를 재시작하지 않도록 함
    ```

#### 7.3.2. Backend 업데이트 (FastAPI App)

FastAPI 애플리케이션 코드 (`fastapi/` 디렉토리 내 파일)가 변경된 경우:

1.  **FastAPI 서비스 이미지 재빌드 및 재시작**:
    ```bash
    docker compose up --build -d fastapi
    ```
    또는
    ```bash
    docker compose build fastapi
    docker compose up -d --no-deps fastapi
    ```

### 7.4. SSL 인증서 갱신

`CERTBOT_GUIDE.md`에 안내된 대로 cron 작업을 설정했다면 인증서는 자동으로 갱신됩니다. 수동으로 갱신 상태를 확인하거나 갱신을 시도하려면 다음 명령을 Nginx 컨테이너 내부 또는 호스트에서 실행할 수 있습니다.

*   **갱신 테스트 (Nginx 컨테이너 내부에서)**:
    ```bash
    docker compose exec nginx certbot renew --dry-run
    ```
*   **실제 갱신 (호스트에서 cron 작업이 실행하는 명령)**:
    ```bash
    docker compose exec nginx certbot renew --quiet
    docker compose exec nginx nginx -s reload
    ```

### 7.5. 데이터 영속성

*   **SSL 인증서**: `/etc/letsencrypt` (Certbot 인증서) 및 `/var/lib/letsencrypt` (Certbot 라이브러리)는 `docker-compose.yml`에 정의된 명명된 볼륨 (`certbot_certs`, `certbot_lib`)을 통해 영속적으로 저장됩니다. 이 볼륨들은 `docker compose down` 시에도 기본적으로 삭제되지 않습니다.
*   **로그**: Nginx 및 FastAPI 로그는 호스트 머신의 `./nginx/logs` 및 `./fastapi/logs` 디렉토리로 마운트되어 영속화됩니다 (설정된 경우).
*   애플리케이션 자체에서 데이터베이스나 파일 저장소를 사용한다면, 해당 데이터도 Docker 볼륨이나 외부 스토리지 서비스를 통해 영속화해야 합니다.

### 7.6. 백업

*   **설정 파일**: `docker-compose.yml`, `nginx/default.conf`, `nginx/nginx.conf`, `fastapi/` 내의 설정 파일 등은 Git을 통해 버전 관리하거나 정기적으로 백업하는 것이 좋습니다.
*   **Docker 볼륨**: Certbot 인증서가 저장된 명명된 볼륨 (`certbot_certs`, `certbot_lib`)은 Docker 볼륨 백업 전략에 따라 백업할 수 있습니다. Docker 볼륨 백업 방법을 검색하여 적절한 절차를 따르십시오.
    *   예시: `docker run --rm -v certbot_certs:/volume -v /path/to/host/backups:/backup ubuntu tar cvf /backup/certbot_certs_backup.tar /volume`

## 8. 문제 해결

*   **서비스 시작 실패**:
    *   `docker compose logs <service_name>`으로 해당 서비스의 로그를 확인하여 오류 메시지를 찾습니다.
    *   포트 충돌: 다른 애플리케이션이 이미 80 또는 443 포트를 사용하고 있는지 확인합니다 (`sudo netstat -tulnp | grep ':80\|:443'`).
    *   Dockerfile 빌드 오류: 빌드 로그를 확인합니다.
*   **웹사이트 접속 불가**:
    *   Azure NSG/방화벽에서 80, 443 포트가 올바르게 열려 있는지 확인합니다.
    *   도메인 DNS 설정이 올바르게 Azure VM의 공인 IP로 연결되어 있는지 확인합니다 (`nslookup YOUR_DOMAIN_HERE`).
    *   Nginx 로그를 확인합니다.
*   **HTTPS/SSL 오류**:
    *   Certbot 발급 과정이 성공했는지 확인합니다 (`CERTBOT_GUIDE.md` 참조).
    *   Nginx 설정 파일 (`nginx/default.conf`가 Certbot에 의해 올바르게 수정되었는지 확인합니다. 컨테이너 내부의 `/etc/nginx/conf.d/default.conf`를 확인).
    *   브라우저의 개발자 도구에서 SSL 관련 오류 메시지를 확인합니다.
*   **API 요청 실패**:
    *   FastAPI 로그를 확인합니다.
    *   Nginx 로그에서 `/api/` 경로 관련 프록시 오류가 있는지 확인합니다.
    *   FastAPI 컨테이너가 정상적으로 실행 중인지 확인합니다 (`docker compose ps`).

이 가이드가 프로젝트를 성공적으로 배포하고 운영하는 데 도움이 되기를 바랍니다. 