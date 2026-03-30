# Keep 开发 Makefile
# 统一本地开发常用命令

.PHONY: help dev dev-ui dev-backend stop lint lint-fe lint-be test test-fe test-be build clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── 开发启动 ──

dev: ## 启动后端 + 前端
	$(MAKE) dev-backend dev-ui

dev-backend: ## 启动后端（Docker）
	docker compose up -d

dev-ui: ## 启动前端（本地，保留汉化）
	cd keep-ui && pnpm install && node scripts/build-monaco-workers-turbopack.js
	cd keep-ui && nohup npx next dev -p 3000 > /tmp/keep-frontend.log 2>&1 &
	@echo "前端日志: tail -f /tmp/keep-frontend.log"

stop: ## 停止所有服务
	docker compose down
	-kill $(lsof -ti :3000) 2>/dev/null
	@echo "已停止"

# ── Lint ──

lint: lint-be lint-fe ## 全量 lint

lint-be: ## Python lint (ruff)
	ruff check keep/ tests/ --fix

lint-fe: ## 前端 lint
	cd keep-ui && npx next lint

# ── 格式化 ──

fmt: fmt-be fmt-fe ## 全量格式化

fmt-be: ## Python 格式化 (black + isort)
	black keep/ tests/
	isort keep/ tests/

fmt-fe: ## 前端格式化 (prettier)
	cd keep-ui && npx prettier --write "app/**/*.{ts,tsx}" "utils/**/*.{ts,tsx}" "components/**/*.{ts,tsx}"

# ── 测试 ──

test: test-be test-fe ## 运行所有测试

test-be: ## Python 单元测试
	cd keep && python -m pytest tests/ --timeout 20 -n auto --non-integration --ignore=tests/e2e_tests/ -v

test-fe: ## 前端单元测试
	cd keep-ui && npx jest --passWithNoTests

# ── Docker ──

build: ## 构建后端镜像
	docker build -t keep-api:local -f Dockerfile.api .

clean: ## 清理 dangling 镜像和已停止的容器
	docker system prune -f
