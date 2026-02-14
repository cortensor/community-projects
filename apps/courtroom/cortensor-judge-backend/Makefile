.PHONY: help install build dev test deploy docker-build docker-up docker-down contracts-build contracts-deploy clean

help:
	@echo "Cortensor Judge Backend - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  make install           Install all dependencies"
	@echo "  make dev              Start development server with hot reload"
	@echo "  make test             Run all tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo "  make lint             Lint all code"
	@echo "  make lint-fix         Fix linting issues"
	@echo "  make typecheck        Run TypeScript type checking"
	@echo ""
	@echo "Smart Contracts:"
	@echo "  make contracts-build   Build Solidity contracts"
	@echo "  make contracts-deploy  Deploy contracts to blockchain"
	@echo ""
	@echo "Production:"
	@echo "  make build            Build production bundles"
	@echo "  make start            Start production server"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start containers"
	@echo "  make docker-down      Stop containers"
	@echo "  make docker-logs      View container logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Clean all build artifacts"
	@echo "  make format           Format all code"
	@echo ""

install:
	npm install --workspaces

build:
	npm run build --workspaces

dev:
	npm run dev -w sentinel

test:
	npm test --workspaces

test-coverage:
	npm run test:coverage --workspaces

lint:
	npm run lint --workspaces

lint-fix:
	npm run lint:fix --workspaces

typecheck:
	npm run typecheck --workspaces

format:
	npm run format --workspaces

contracts-build:
	cd contracts && forge build

contracts-deploy:
	cd contracts && forge script script/Deploy.s.sol:DeployJudge --broadcast --verify

start:
	npm start -w sentinel

docker-build:
	docker build -f docker/Dockerfile -t cortensor-judge:latest .

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f sentinel

docker-ps:
	docker-compose -f docker/docker-compose.yml ps

clean:
	rm -rf sentinel/dist sentinel/node_modules judge-sdk/dist judge-sdk/node_modules
	rm -rf contracts/out contracts/cache
	rm -rf coverage .nyc_output
	find . -name "*.log" -delete

.DEFAULT_GOAL := help
