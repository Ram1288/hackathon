#!/bin/bash
# DevDebug AI - Quick Demo Script
# Demonstrates key features for hackathon

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         DevDebug AI - Interactive Demo                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

wait_for_enter() {
    echo ""
    echo -e "${YELLOW}Press ENTER to continue...${NC}"
    read
}

# Step 1: Health Check
print_step "Step 1: System Health Check"
echo "Let's verify all agents are working..."
wait_for_enter

python3 integrations/standalone.py health

wait_for_enter

# Step 2: Simple Troubleshooting
print_step "Step 2: CrashLoopBackOff Troubleshooting"
echo "Query: My pod is in CrashLoopBackOff state"
wait_for_enter

python3 integrations/standalone.py troubleshoot \
  --query "My pod is in CrashLoopBackOff state" \
  --namespace default

wait_for_enter

# Step 3: ImagePullBackOff
print_step "Step 3: ImagePullBackOff Error"
echo "Query: ImagePullBackOff error on my deployment"
wait_for_enter

python3 integrations/standalone.py troubleshoot \
  --query "ImagePullBackOff error on my deployment" \
  --namespace production

wait_for_enter

# Step 4: Code Generation
print_step "Step 4: Python Code Generation"
echo "Query: Generate a Python script to monitor pod health"
wait_for_enter

python3 integrations/standalone.py troubleshoot \
  --query "Generate a Python script to list all pods with their status and resource usage"

wait_for_enter

# Step 5: Interactive Mode Demo
print_step "Step 5: Interactive Mode"
echo "Now entering interactive mode. Try these queries:"
echo "  - Pod keeps getting OOMKilled"
echo "  - Show me kubectl commands for debugging"
echo "  - /health (to check system status)"
echo "  - exit (to quit)"
echo ""
wait_for_enter

python3 integrations/standalone.py interactive

# Summary
print_step "Demo Complete! 🎉"
echo "What we demonstrated:"
echo ""
echo "  ✓ Multi-agent architecture (Document + Execution + LLM)"
echo "  ✓ Intelligent pattern recognition for K8s issues"
echo "  ✓ Automated diagnostics and code generation"
echo "  ✓ Multiple interfaces (CLI shown, API available)"
echo "  ✓ Production-ready modular design"
echo ""
echo "Next steps:"
echo "  • Start API: python3 integrations/rest_api.py"
echo "  • Visit API docs: http://localhost:8000/docs"
echo "  • Add custom docs to ./docs/"
echo ""
echo "Happy troubleshooting! 🚀"
