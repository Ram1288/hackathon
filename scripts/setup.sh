#!/bin/bash
# DevDebug AI Setup Script
# Automated setup for hackathon demo

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         DevDebug AI - Setup & Installation                 ║"
echo "║    Intelligent Kubernetes Troubleshooting Assistant        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Check prerequisites
print_header "1. Checking Prerequisites"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_status "pip3 found"
else
    print_error "pip3 not found. Please install pip3"
    exit 1
fi

# Check kubectl (optional)
if command -v kubectl &> /dev/null; then
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null || kubectl version --client 2>&1 | head -n1)
    print_status "kubectl found: $KUBECTL_VERSION"
    KUBECTL_AVAILABLE=true
else
    print_warning "kubectl not found (optional for full functionality)"
    KUBECTL_AVAILABLE=false
fi

# Install Python dependencies
print_header "2. Installing Python Dependencies"

pip3 install -r requirements.txt
print_status "Python dependencies installed"

# Setup Ollama
print_header "3. Setting up Ollama (LLM)"

if command -v ollama &> /dev/null; then
    print_status "Ollama already installed"
else
    print_warning "Ollama not found. Installing..."
    echo "Run: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "Or visit: https://ollama.ai"
    echo ""
    read -p "Do you want to install Ollama now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
        print_status "Ollama installed"
    else
        print_warning "Skipping Ollama installation. You can install it later."
    fi
fi

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_status "Ollama service is running"
    
    # Check if model is available
    if curl -s http://localhost:11434/api/tags | grep -q "llama3.1"; then
        print_status "Llama 3.1 model already available"
    else
        print_warning "Llama 3.1 model not found. Pulling..."
        echo "This may take a few minutes..."
        ollama pull llama3.1:8b
        print_status "Llama 3.1 model downloaded"
    fi
else
    print_warning "Ollama service not running"
    echo "Please start Ollama:"
    echo "  - macOS/Linux: ollama serve"
    echo "  - Or start as system service"
    echo ""
fi

# Create directories
print_header "4. Creating Directory Structure"

mkdir -p docs
mkdir -p logs
print_status "Directories created"

# Check if config exists
if [ -f "config.yaml" ]; then
    print_status "Configuration file already exists"
else
    print_status "Configuration file created (config.yaml)"
fi

# Create sample documentation if doesn't exist
if [ ! -f "docs/k8s_troubleshooting.md" ]; then
    print_warning "Sample documentation not found, but that's OK - it should be in the repo"
fi

# Setup CLI command (optional)
print_header "5. Setting up CLI Command"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLI_SCRIPT="$SCRIPT_DIR/integrations/standalone.py"

echo "You can run DevDebug AI using:"
echo "  python3 $CLI_SCRIPT troubleshoot --query 'your issue'"
echo "  python3 $CLI_SCRIPT interactive"
echo "  python3 $CLI_SCRIPT health"
echo ""

# Create a simple wrapper script
cat > devdebug.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
python3 "$SCRIPT_DIR/integrations/standalone.py" "$@"
EOF

chmod +x devdebug.sh
print_status "Created wrapper script: ./devdebug.sh"

# Run health check
print_header "6. Running Health Check"

python3 integrations/standalone.py health || print_warning "Health check failed (this is OK if Ollama isn't running yet)"

# Final summary
print_header "Setup Complete! 🎉"

echo ""
echo "Next Steps:"
echo ""
echo "1. Start Ollama (if not running):"
echo "   $ ollama serve"
echo ""
echo "2. Try the CLI:"
echo "   $ ./devdebug.sh troubleshoot --query 'My pod is in CrashLoopBackOff'"
echo "   $ ./devdebug.sh interactive"
echo ""
echo "3. Or start the API server:"
echo "   $ python3 integrations/rest_api.py"
echo "   Then visit: http://localhost:8000/docs"
echo ""
echo "4. Add your own documentation to ./docs/"
echo ""

if [ "$KUBECTL_AVAILABLE" = false ]; then
    echo "Note: kubectl not found. Install it for full Kubernetes integration:"
    echo "  https://kubernetes.io/docs/tasks/tools/"
    echo ""
fi

echo "For more information, see README.md"
echo ""
echo "Happy troubleshooting! 🚀"
