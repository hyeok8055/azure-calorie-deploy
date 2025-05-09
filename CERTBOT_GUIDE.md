# Docker 컨테이너 내 Certbot을 이용한 SSL 인증서 발급 및 갱신 가이드 (Nginx)

이 가이드는 Docker Compose로 실행 중인 Nginx 컨테이너 내에서 Certbot을 사용하여 Let's Encrypt SSL 인증서를 발급받고, 자동으로 갱신하도록 설정하는 과정을 안내합니다.

**사전 준비 사항:**

1.  **도메인**: SSL 인증서를 발급받을 유효한 도메인 이름이 필요합니다. 이 도메인은 Azure VM 인스턴스의 공인 IP 주소 (`20.39.191.188`)를 가리키도록 DNS 설정이 완료되어 있어야 합니다.
    *   **주의**: Let's Encrypt는 IP 주소에 대해 인증서를 발급하지 않습니다.
2.  **필수 파일 수정**:
    *   `nginx/default.conf` 파일의 `server_name YOUR_DOMAIN_HERE;` 부분을 **실제 사용자의 도메인 이름으로 변경**합니다. (예: `server_name example.com www.example.com;`)
3.  **Azure 방화벽 (NSG)**: TCP 포트 80 (HTTP) 및 443 (HTTPS)이 외부에서 Azure VM 인스턴스로 접근 가능하도록 열려 있어야 합니다.
4.  **Docker 및 Docker Compose**: Azure VM 인스턴스에 설치되어 있어야 합니다.

**단계별 안내:**

**1단계: 초기 Docker 컨테이너 실행**

프로젝트의 루트 디렉토리 ( `docker-compose.yml` 파일이 있는 위치)에서 다음 명령을 실행하여 Nginx 및 FastAPI 컨테이너를 시작합니다.

```bash
docker compose up --build -d
```

*   이 시점에서 Nginx는 HTTP (80번 포트)로만 서비스될 수 있으며, `nginx/default.conf`에 설정된 `server_name`으로 접속을 시도합니다.
*   SSL 인증서가 아직 없으므로 HTTPS 접속은 실패하거나 경고가 발생할 수 있습니다.

**2단계: Nginx 컨테이너 접속**

실행 중인 Nginx 컨테이너 내부로 접속합니다.

```bash
docker compose exec nginx sh
```

(또는 `docker compose exec nginx bash` 사용 가능)

**3단계: Certbot을 이용한 SSL 인증서 발급**

Nginx 컨테이너 내부 쉘에서 다음 Certbot 명령을 실행합니다. **`YOUR_DOMAIN_HERE`는 실제 도메인 이름으로, `your_email@example.com`은 실제 이메일 주소로 변경**해야 합니다.

```bash
certbot --nginx -d YOUR_DOMAIN_HERE -d www.YOUR_DOMAIN_HERE --non-interactive --agree-tos -m your_email@example.com --redirect
```

*   `-d YOUR_DOMAIN_HERE`: 주 도메인을 지정합니다.
*   `-d www.YOUR_DOMAIN_HERE`: www 서브도메인도 함께 인증받으려면 추가합니다 (선택 사항).
*   `--nginx`: Nginx 플러그인을 사용하여 Nginx 설정을 자동으로 감지하고 수정합니다.
*   `--non-interactive`: 대화형 프롬프트 없이 실행합니다.
*   `--agree-tos`: Let's Encrypt 서비스 약관에 동의합니다.
*   `-m your_email@example.com`: 인증서 만료 알림 등을 받을 이메일 주소입니다.
*   `--redirect`: HTTP 요청을 HTTPS로 자동으로 리디렉션하도록 Nginx 설정을 수정합니다.

Certbot이 성공적으로 인증서를 발급받으면, `/etc/letsencrypt/live/YOUR_DOMAIN_HERE/` 디렉토리에 인증서 파일들이 생성되고, `nginx/default.conf` (컨테이너 내부 경로) 파일이 SSL을 사용하도록 자동으로 업데이트됩니다.

**4단계: Nginx 설정 리로드 (Certbot이 자동으로 시도할 수 있음)**

Certbot `--nginx` 플러그인은 일반적으로 Nginx 설정을 자동으로 리로드합니다. 만약 자동으로 리로드되지 않았거나, 수동으로 확인하고 싶다면 Nginx 컨테이너 내부에서 다음 명령을 실행합니다.

```bash
nginx -t # 설정 파일 문법 검사
nginx -s reload # Nginx 설정 리로드
```

이제 `https://YOUR_DOMAIN_HERE`로 접속하여 HTTPS가 정상적으로 적용되었는지 확인합니다. HTTP로 접속 시 자동으로 HTTPS로 리디렉션되어야 합니다.

**5단계: 인증서 자동 갱신 설정**

Let's Encrypt 인증서는 90일 동안 유효합니다. 만료되기 전에 자동으로 갱신되도록 설정해야 합니다.

Nginx 컨테이너 내에서 Certbot의 갱신 테스트를 실행해 볼 수 있습니다:

```bash
certbot renew --dry-run
```

실제 갱신은 호스트 머신 또는 컨테이너 내에서 cron 작업을 설정하여 주기적으로 `certbot renew` 명령을 실행하도록 합니다.
Docker 환경에서는 호스트에서 cron 작업을 설정하고 `docker compose exec nginx certbot renew`를 실행하는 것이 일반적인 방법 중 하나입니다.

**호스트 머신에서 Cron 작업 설정 예시 (매일 두 번 실행):**

호스트 머신에서 `crontab -e`를 실행하고 다음 줄을 추가합니다 (프로젝트 경로를 실제 경로로 변경):

```cron
0 0,12 * * * cd /path/to/your/project && docker compose exec nginx certbot renew --quiet && docker compose exec nginx nginx -s reload
```

*   `--quiet`: 성공적인 갱신 시에는 출력을 최소화합니다.
*   갱신 후에는 Nginx 설정을 리로드하여 새 인증서를 적용해야 합니다.

**컨테이너 내부에서 Cron 설정 (덜 일반적이지만 가능):**

만약 Nginx 컨테이너에 cron 데몬이 설치되어 있다면 (기본 `nginx:alpine` 이미지에는 없음), 컨테이너 내부에 cron 작업을 설정할 수도 있습니다. 이 경우 Dockerfile을 수정하여 cron을 설치하고 설정해야 합니다.

**문제 해결:**

*   **도메인 확인 실패**: DNS 설정이 올바르게 전파되었는지 확인합니다. `nslookup YOUR_DOMAIN_HERE` 등으로 IP 주소를 확인합니다.
*   **포트 차단**: Azure NSG 또는 로컬 방화벽에서 80, 443 포트가 열려 있는지 다시 확인합니다.
*   **Certbot 로그**: 문제 발생 시 `/var/log/letsencrypt/letsencrypt.log` (컨테이너 내부) 파일을 확인합니다.
*   **Nginx 로그**: `docker compose logs nginx` 명령으로 Nginx 로그를 확인합니다.

이 가이드를 통해 성공적으로 SSL 인증서를 설정하고 웹사이트를 안전하게 운영하시기 바랍니다. 