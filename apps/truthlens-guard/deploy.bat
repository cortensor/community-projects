@echo off
REM TruthLens Deployment Script for Windows
REM Supports deployment to Vercel (frontend) and Render (backend)

echo 🚀 TruthLens Deployment Script
echo ===============================

REM Colors (Windows CMD doesn't support ANSI colors well, so we'll use plain text)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Node.js is not installed. Please install Node.js first.
    pause
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% npm is not installed. Please install npm first.
    pause
    exit /b 1
)

echo %SUCCESS% Dependencies check passed

:menu
echo.
echo Select deployment option:
echo 1^) Deploy frontend to Vercel
echo 2^) Deploy backend to Render ^(Node.js^)
echo 3^) Deploy with Docker to Render
echo 4^) Deploy both ^(Vercel + Render^)
echo 5^) Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto deploy_vercel
if "%choice%"=="2" goto deploy_render
if "%choice%"=="3" goto deploy_docker
if "%choice%"=="4" goto deploy_both
if "%choice%"=="5" goto exit_script

echo %ERROR% Invalid choice. Please select 1-5.
goto menu

:deploy_vercel
echo %INFO% Deploying frontend to Vercel...

REM Check if Vercel CLI is installed
vercel --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %WARNING% Vercel CLI not found. Installing...
    npm install -g vercel
)

REM Check if logged in to Vercel
vercel whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo %WARNING% Please login to Vercel first:
    vercel login
    if %errorlevel% neq 0 (
        echo %ERROR% Vercel login failed.
        pause
        exit /b 1
    )
)

REM Deploy
echo %INFO% Building and deploying to Vercel...
vercel --prod

if %errorlevel% equ 0 (
    echo %SUCCESS% Frontend deployed to Vercel!
    echo %INFO% Note: Update vercel.json with your Render backend URL
) else (
    echo %ERROR% Vercel deployment failed.
)
goto end

:deploy_render
echo %INFO% Deploying backend to Render...

REM Check if Render CLI is installed
render --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %WARNING% Render CLI not found. Installing...
    npm install -g render-cli
)

REM Check if logged in to Render
render whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo %WARNING% Please login to Render first:
    render login
    if %errorlevel% neq 0 (
        echo %ERROR% Render login failed.
        pause
        exit /b 1
    )
)

REM Deploy using render.yaml
echo %INFO% Deploying using render.yaml configuration...
render deploy

if %errorlevel% equ 0 (
    echo %SUCCESS% Backend deployed to Render!
) else (
    echo %ERROR% Render deployment failed.
)
goto end

:deploy_docker
echo %INFO% Deploying with Docker to Render...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Docker is not installed. Please install Docker first.
    pause
    exit /b 1
)

REM Build Docker image
echo %INFO% Building Docker image...
docker build -t truthlens .

if %errorlevel% neq 0 (
    echo %ERROR% Docker build failed.
    pause
    exit /b 1
)

REM Tag for Render
echo %INFO% Tagging image for Render...
docker tag truthlens registry.render.com/truthlens

REM Login to Render registry (user will need to provide credentials)
echo %WARNING% Please ensure you're logged in to Render registry
echo %INFO% Pushing to Render registry...
docker push registry.render.com/truthlens

if %errorlevel% equ 0 (
    echo %SUCCESS% Docker image pushed to Render!
    echo %INFO% Create a new Render service with Docker and use: registry.render.com/truthlens
) else (
    echo %ERROR% Docker push failed.
)
goto end

:deploy_both
echo %INFO% Deploying both frontend and backend...
call :deploy_vercel
echo.
call :deploy_render
goto end

:exit_script
echo %INFO% Goodbye!
goto end

:end
echo.
echo Deployment script completed.
pause
