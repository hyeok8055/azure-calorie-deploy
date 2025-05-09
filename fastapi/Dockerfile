FROM python:3.11-slim

# 시스템 패키지 업데이트 및 빌드 도구 설치 (선택적, 크롤링 안정성↑)
RUN apt-get update && apt-get install -y curl build-essential && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사는 생략 (개발용에선 볼륨 마운트로 대체)
# COPY . .

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 개발용 커맨드 (자동 reload, 디버그 로그)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "20100", "--reload", "--log-level", "debug"]
