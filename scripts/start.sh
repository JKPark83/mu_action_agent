#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  echo ""
  echo "서버를 종료합니다..."
  kill 0 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# .env 파일 확인
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "[오류] .env 파일이 없습니다. 먼저 'cp .env.example .env'로 생성하세요."
  exit 1
fi

# 백엔드 실행
echo "[백엔드] 의존성 설치 중..."
cd "$ROOT_DIR/backend"
uv sync --quiet

echo "[백엔드] 서버 시작 (port 8000)..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 프론트엔드 실행
echo "[프론트엔드] 의존성 설치 중..."
cd "$ROOT_DIR/frontend"
npm install --silent

echo "[프론트엔드] 서버 시작 (port 5173)..."
npm run dev &

echo ""
echo "============================================"
echo "  프론트엔드 : http://localhost:5173"
echo "  백엔드 API : http://localhost:8000/docs"
echo "  종료: Ctrl+C"
echo "============================================"
echo ""

wait
