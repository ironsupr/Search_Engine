# EchoSearch Docker Helper Script
# Run with: .\docker-run.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host @"
EchoSearch Docker Helper
========================

Usage: .\docker-run.ps1 [command]

Commands:
  start       Start all services (frontend, backend, infrastructure)
  stop        Stop all services
  restart     Restart all services
  logs        Show logs from all services
  logs-api    Show backend API logs
  logs-web    Show frontend logs
  build       Rebuild all containers
  clean       Stop and remove all containers, networks, volumes
  status      Show status of all services
  workers     Start with background workers (crawler + indexer)
  shell       Open shell in backend container
  help        Show this help message

Examples:
  .\docker-run.ps1 start      # Start the application
  .\docker-run.ps1 logs-api   # View backend logs
  .\docker-run.ps1 workers    # Start with crawler and indexer
"@
}

function Start-Services {
    Write-Host "Starting EchoSearch services..." -ForegroundColor Green
    docker-compose up -d --build
    Write-Host "`nServices started! Access:" -ForegroundColor Green
    Write-Host "  Frontend: http://localhost" -ForegroundColor Cyan
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "  RabbitMQ: http://localhost:15672" -ForegroundColor Cyan
}

function Start-WithWorkers {
    Write-Host "Starting EchoSearch with workers..." -ForegroundColor Green
    docker-compose --profile workers up -d --build
    Write-Host "`nServices started with crawler and indexer!" -ForegroundColor Green
}

function Stop-Services {
    Write-Host "Stopping EchoSearch services..." -ForegroundColor Yellow
    docker-compose down
}

function Restart-Services {
    Write-Host "Restarting EchoSearch services..." -ForegroundColor Yellow
    docker-compose restart
}

function Show-Logs {
    docker-compose logs -f
}

function Show-ApiLogs {
    docker-compose logs -f backend
}

function Show-WebLogs {
    docker-compose logs -f frontend
}

function Build-Services {
    Write-Host "Rebuilding EchoSearch containers..." -ForegroundColor Green
    docker-compose build --no-cache
}

function Clean-All {
    Write-Host "Cleaning up all Docker resources..." -ForegroundColor Red
    docker-compose down -v --remove-orphans
    Write-Host "Cleaned!" -ForegroundColor Green
}

function Show-Status {
    docker-compose ps
}

function Open-Shell {
    docker exec -it echosearch-backend /bin/bash
}

switch ($Command.ToLower()) {
    "start"    { Start-Services }
    "stop"     { Stop-Services }
    "restart"  { Restart-Services }
    "logs"     { Show-Logs }
    "logs-api" { Show-ApiLogs }
    "logs-web" { Show-WebLogs }
    "build"    { Build-Services }
    "clean"    { Clean-All }
    "status"   { Show-Status }
    "workers"  { Start-WithWorkers }
    "shell"    { Open-Shell }
    default    { Show-Help }
}
