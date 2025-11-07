# 🏗️ DevDebug AI

**Intelligent Kubernetes Troubleshooting Assistant**

DevDebug AI is an AI-powered troubleshooting system that combines RAG (Retrieval-Augmented Generation), diagnostic execution, and LLM intelligence to help debug Kubernetes and RHEL systems.

## 🌟 Features

- **🔍 Intelligent Documentation Search (RAG)**: Automatically finds relevant documentation for your issue
- **⚡ Automated Diagnostics**: Runs kubectl commands and system diagnostics
- **🤖 AI-Powered Solutions**: Uses Llama 3.1 to generate step-by-step solutions
- **📊 Pattern Recognition**: Recognizes common K8s issues (CrashLoopBackOff, ImagePullBackOff, OOMKilled, etc.)
- **💻 Multiple Interfaces**: CLI, REST API, and ready for kAgent integration
- **🔒 Safety First**: Command validation and execution restrictions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DevDebug AI Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Core Orchestration Layer                 │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │  Message   │  │   Decision   │  │   Response  │ │   │
│  │  │   Router   │→ │    Engine    │→ │  Formatter  │ │   │
│  │  └────────────┘  └──────────────┘  └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Agent Abstraction Layer                 │   │
│  │       ┌─────────────┐  ┌─────────────┐  ┌─────────┐│   │
│  │       │Doc Agent    │  │Exec Agent   │  │  LLM    ││   │
│  │       │   (RAG)     │  │(RHEL/K8s)   │  │ Agent   ││   │
│  │       └─────────────┘  └─────────────┘  └─────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Integration Layer                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │Standalone│  │  kAgent  │  │     REST API     │  │   │
│  │  │   CLI    │  │  Plugin  │  │    Interface     │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- kubectl (optional, for K8s integration)
- Ollama with Llama 3.1 (for AI features)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd devdebug-ai

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# 4. Pull Llama model
ollama pull llama3.1:8b

# 5. Start Ollama (in a separate terminal)
ollama serve
```

### Quick Test

```bash
# Option 1: Using the wrapper script
./devdebug.sh troubleshoot --query "My pod is in CrashLoopBackOff"

# Option 2: Direct Python
python3 integrations/standalone.py troubleshoot --query "My pod is crashing"

# Option 3: Interactive mode
./devdebug.sh interactive
```

## 💻 Usage Examples

### CLI Interface

#### Single Query

```bash
# Basic troubleshooting
python3 integrations/standalone.py troubleshoot \
  --query "My pod is in CrashLoopBackOff state" \
  --namespace production

# With specific pod
python3 integrations/standalone.py troubleshoot \
  --query "Pod keeps restarting" \
  --namespace default \
  --pod api-server-xyz
```

#### Interactive Mode

```bash
python3 integrations/standalone.py interactive

# Special commands in interactive mode:
# /namespace <name>  - Change namespace
# /clear            - Clear session
# /health           - Check system health
# exit or quit      - Exit
```

#### Health Check

```bash
python3 integrations/standalone.py health
```

### REST API

#### Start the API Server

```bash
python3 integrations/rest_api.py

# Or with uvicorn
uvicorn integrations.rest_api:app --reload --port 8000
```

#### API Endpoints

```bash
# Query endpoint
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My pod is in CrashLoopBackOff",
    "namespace": "default"
  }'

# Health check
curl http://localhost:8000/health

# Get examples
curl http://localhost:8000/examples

# API documentation (Swagger UI)
# Visit: http://localhost:8000/docs
```

## 📚 Example Queries

Here are some example queries you can try:

```bash
# Pod Issues
"My pod is in CrashLoopBackOff"
"ImagePullBackOff error on deployment"
"Pod keeps getting OOMKilled"
"Pod is stuck in Pending state"

# Cluster Diagnostics
"Show me all failing pods in production"
"Check node resource usage"
"What warning events happened recently?"

# Code Generation
"Generate a Python script to list all pods with resource limits"
"Write kubectl commands to troubleshoot networking"
"Show me how to check pod logs in Python"

# Log Analysis
"Analyze these logs and identify the issue"
"What's wrong with my application logs?"
```

## 📁 Project Structure

```
devdebug-ai/
├── core/
│   ├── __init__.py
│   ├── interfaces.py          # Base agent interfaces
│   └── orchestrator.py        # Main orchestration engine
├── agents/
│   ├── __init__.py
│   ├── document_agent.py      # RAG document search
│   ├── execution_agent.py     # K8s diagnostics
│   └── llm_agent.py          # Ollama LLM interface
├── integrations/
│   ├── standalone.py          # CLI interface
│   ├── rest_api.py           # REST API
│   └── kagent_plugin.py      # kAgent integration (future)
├── docs/
│   └── k8s_troubleshooting.md # Sample documentation
├── config.yaml               # Configuration
├── requirements.txt          # Python dependencies
├── setup.sh                 # Setup script
└── README.md               # This file
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# Document Agent
document_agent:
  doc_dir: ./docs

# Execution Agent
execution_agent:
  ssh_enabled: false
  kubeconfig_path: ~/.kube/config

# LLM Agent
llm_agent:
  ollama_url: http://localhost:11434
  model: llama3.1:8b
  temperature: 0.7

# Orchestrator
orchestrator:
  max_session_history: 100
  session_timeout: 3600
```

## 🔧 Adding Custom Documentation

Add your own troubleshooting guides to the `docs/` directory:

```bash
# Create a new documentation file
cat > docs/my_custom_guide.md << EOF
# My Custom Troubleshooting Guide

## Issue: Custom Application Error

**Diagnosis:**
\`\`\`bash
kubectl logs my-app -n namespace
\`\`\`

**Solution:**
1. Check configuration
2. Restart the pod

\`\`\`python
from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
# Your Python code here
\`\`\`
EOF
```

The Document Agent will automatically index and search these files!

## 🎯 Key Components

### 1. Document Agent (RAG)
- Indexes Markdown documentation
- Keyword-based search
- Extracts code examples (Python & kubectl)
- Recognizes K8s patterns

### 2. Execution Agent
- Runs kubectl commands safely
- Executes system diagnostics
- Supports SSH for remote execution
- Command validation for security

### 3. LLM Agent
- Interfaces with Ollama (Llama 3.1)
- Multiple prompt templates:
  - Troubleshooting
  - Log analysis
  - Code generation
  - Explanation
  - Optimization
- Fallback mode when LLM unavailable

### 4. Orchestrator
- Coordinates all agents
- Maintains session context
- Implements the RAG → Execute → LLM pipeline

## 🔒 Security Features

- Command validation and forbidden patterns
- No destructive operations by default
- Configurable allowed commands
- SSH key-based authentication
- No storage of sensitive data

## 🐛 Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check model availability
ollama list
```

### kubectl Not Found

```bash
# The system works without kubectl but with limited functionality
# Install kubectl: https://kubernetes.io/docs/tasks/tools/

# Verify kubectl
kubectl version --client
```

### Agent Initialization Errors

```bash
# Run health check
python3 integrations/standalone.py health

# Check configuration
cat config.yaml

# Verify Python dependencies
pip3 install -r requirements.txt
```

## 🚀 Future Enhancements

- [ ] kAgent plugin integration
- [ ] Semantic search with embeddings
- [ ] Real-time monitoring dashboard
- [ ] Multi-cluster support
- [ ] Custom plugin system
- [ ] Historical issue tracking
- [ ] Automated fix application
- [ ] Integration with ticketing systems

## 🤝 Contributing

This is a hackathon project! Feel free to:
- Add more documentation to `docs/`
- Improve agent logic
- Add new prompt templates
- Enhance the CLI/API interfaces

## 📝 License

MIT License - Feel free to use and modify!

## 🎓 Hackathon Demo Tips

### Quick Demo Script

```bash
# 1. Start with a simple query
./devdebug.sh troubleshoot --query "Pod in CrashLoopBackOff"

# 2. Show interactive mode
./devdebug.sh interactive
> My pod keeps restarting
> Generate Python script to check pod health

# 3. Demonstrate API
python3 integrations/rest_api.py &
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"query": "OOMKilled error"}'

# 4. Show health check
./devdebug.sh health
```

### Key Talking Points

1. **Three-Agent Architecture**: RAG + Execution + LLM working together
2. **Smart Pattern Recognition**: Automatically recognizes common K8s issues
3. **Multiple Interfaces**: CLI, API, ready for kAgent
4. **Production-Ready**: Modular, configurable, secure
5. **Extensible**: Easy to add new documentation and agents

## 📧 Contact

Created for the Hackathon 2024

---

**Happy Troubleshooting! 🚀**
