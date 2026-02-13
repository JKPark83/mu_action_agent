#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# --debug 플래그 확인
DEBUG_MODE=false
for arg in "$@"; do
  case "$arg" in
    --debug) DEBUG_MODE=true ;;
  esac
done

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

if [ "$DEBUG_MODE" = true ]; then
  echo "[백엔드] 서버 시작 (port 8000, DEBUG 모드)..."
  DEBUG=true uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug &
else
  echo "[백엔드] 서버 시작 (port 8000)..."
  DEBUG=false uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level warning &
fi

# 프론트엔드 실행
echo "[프론트엔드] 의존성 설치 중..."
cd "$ROOT_DIR/frontend"
npm install --silent

if [ "$DEBUG_MODE" = true ]; then
  echo "[프론트엔드] 서버 시작 (port 5173, DEBUG 모드)..."
  VITE_DEBUG=true npm run dev &
else
  echo "[프론트엔드] 서버 시작 (port 5173)..."
  npm run dev &
fi

echo ""
echo "============================================"
if [ "$DEBUG_MODE" = true ]; then
  echo "  모드       : DEBUG"
fi
echo "  프론트엔드 : http://localhost:5173"
echo "  백엔드 API : http://localhost:8000/docs"
echo "  종료: Ctrl+C"
echo "============================================"
echo ""

wait
