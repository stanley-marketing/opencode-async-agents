#!/bin/bash
# Deployment script for OpenCode-Slack Agent Orchestration System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="opencode-slack"
ENVIRONMENT="${1:-development}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f ".env.${ENVIRONMENT}" ]]; then
        log_error "Environment file .env.${ENVIRONMENT} not found."
        log_info "Please create .env.${ENVIRONMENT} based on the template."
        exit 1
    fi
    
    log_success "All requirements met"
}

setup_directories() {
    log_info "Setting up directories..."
    
    # Create necessary directories
    mkdir -p data logs sessions ssl monitoring
    
    # Set proper permissions
    chmod 755 data logs sessions
    chmod 700 ssl
    
    log_success "Directories created"
}

validate_configuration() {
    log_info "Validating configuration..."
    
    # Check for required environment variables
    source ".env.${ENVIRONMENT}"
    
    required_vars=("OPENAI_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        log_info "Please update .env.${ENVIRONMENT} with the required values."
        exit 1
    fi
    
    log_success "Configuration validated"
}

build_images() {
    log_info "Building Docker images..."
    
    # Build the appropriate target
    if [[ "$ENVIRONMENT" == "production" ]]; then
        docker-compose build opencode-slack-prod
    else
        docker-compose build opencode-slack-dev
    fi
    
    log_success "Docker images built"
}

deploy_application() {
    log_info "Deploying application..."
    
    # Stop existing containers
    docker-compose --profile "$ENVIRONMENT" down
    
    # Start new containers
    if [[ "$ENVIRONMENT" == "production" ]]; then
        docker-compose --profile prod up -d
    else
        docker-compose --profile dev up -d
    fi
    
    log_success "Application deployed"
}

wait_for_health() {
    log_info "Waiting for application to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_success "Application is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for health check..."
        sleep 5
        ((attempt++))
    done
    
    log_error "Application failed to become healthy"
    return 1
}

show_status() {
    log_info "Application status:"
    docker-compose --profile "$ENVIRONMENT" ps
    
    log_info "Application logs (last 20 lines):"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        docker-compose logs --tail=20 opencode-slack-prod
    else
        docker-compose logs --tail=20 opencode-slack-dev
    fi
}

cleanup() {
    log_info "Cleaning up old images..."
    docker image prune -f
    log_success "Cleanup completed"
}

# Main deployment flow
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT"
    
    cd "$SCRIPT_DIR"
    
    check_requirements
    setup_directories
    validate_configuration
    build_images
    deploy_application
    
    if wait_for_health; then
        show_status
        cleanup
        
        log_success "Deployment completed successfully!"
        log_info "Application is running at: http://localhost:8080"
        log_info "Health check: http://localhost:8080/health"
        log_info "Status endpoint: http://localhost:8080/status"
    else
        log_error "Deployment failed - application is not healthy"
        show_status
        exit 1
    fi
}

# Help function
show_help() {
    echo "Usage: $0 [ENVIRONMENT]"
    echo ""
    echo "Deploy OpenCode-Slack Agent Orchestration System"
    echo ""
    echo "Arguments:"
    echo "  ENVIRONMENT    Deployment environment (development|production) [default: development]"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy to development"
    echo "  $0 development        # Deploy to development"
    echo "  $0 production         # Deploy to production"
    echo ""
    echo "Requirements:"
    echo "  - Docker and Docker Compose installed"
    echo "  - .env.ENVIRONMENT file configured"
    echo ""
}

# Parse arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    development|production|"")
        main
        ;;
    *)
        log_error "Invalid environment: $1"
        show_help
        exit 1
        ;;
esac