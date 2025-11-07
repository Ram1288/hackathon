# 🚀 DevDebug AI - Quick Start Guide

## 5-Minute Setup

### Prerequisites Check
```bash
# Verify you have Python 3.8+
python3 --version

# Verify pip
pip3 --version

# Optional but recommended
kubectl version --client
```

### Installation

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Install Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh

# 3. Pull Llama model
ollama pull llama3.1:8b

# 4. Start Ollama (in a separate terminal)
ollama serve
```

### First Test

```bash
# Check system health
python3 integrations/standalone.py health

# Expected output:
# ✓ document: healthy
# ✓ execution: healthy  
# ✓ llm: healthy (or fallback mode if Ollama not running)
```

### Your First Query

```bash
python3 integrations/standalone.py troubleshoot \
  --query "My pod is in CrashLoopBackOff state"
```

You should see:
1. 📚 Documentation search results
2. 🔍 Diagnostic execution
3. 💡 AI-generated solution
4. 📊 K8s pattern recognition

## Common Commands

### CLI Usage

```bash
# Single query
./devdebug.sh troubleshoot --query "YOUR_ISSUE" --namespace default

# Interactive mode
./devdebug.sh interactive

# Health check
./devdebug.sh health

# Run demo
./demo.sh
```

### API Usage

```bash
# Start API server
python3 integrations/rest_api.py

# In another terminal, test it
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Pod keeps crashing", "namespace": "default"}'

# Visit Swagger docs
# http://localhost:8000/docs
```

## Example Queries to Try

```bash
# 1. Pod Issues
"My pod is in CrashLoopBackOff"
"ImagePullBackOff error"
"Pod keeps getting OOMKilled"

# 2. Diagnostics
"Show me all failing pods"
"Check node resource usage"
"What's wrong with my deployment?"

# 3. Code Generation
"Generate Python script to list all pods"
"Show me kubectl commands for debugging"
"Write code to monitor pod health"

# 4. General Questions
"Explain Kubernetes resource limits"
"How do I troubleshoot networking?"
"Best practices for pod health checks"
```

## Interactive Mode Commands

When in interactive mode:
- `/namespace <name>` - Switch namespace
- `/clear` - Clear current session
- `/health` - Check system health
- `exit` or `quit` - Exit interactive mode

## Troubleshooting Setup

### Ollama Not Running
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull model if missing
ollama pull llama3.1:8b
```

### kubectl Not Found
```bash
# System works without kubectl but with limited features
# To install:
# macOS: brew install kubectl
# Linux: https://kubernetes.io/docs/tasks/tools/
```

### Python Dependencies
```bash
# Reinstall if needed
pip3 install -r requirements.txt --force-reinstall
```

## Verify Everything Works

```bash
# Run the test suite
python3 tests/test_components.py

# Should see:
# ✓ Interface tests passed
# ✓ Document Agent tests passed
# ✓ Execution Agent tests passed
# ✓ LLM Agent tests passed
# ✓ Orchestrator tests passed
```

## Next Steps

1. **Add Custom Documentation**
   ```bash
   # Create new .md file in docs/
   cp my_guide.md docs/
   ```

2. **Configure for Your Environment**
   ```bash
   # Edit config.yaml
   vi config.yaml
   ```

3. **Run the Demo**
   ```bash
   ./demo.sh
   ```

4. **Deploy the API**
   ```bash
   # Start API server
   uvicorn integrations.rest_api:app --host 0.0.0.0 --port 8000
   ```

## Getting Help

- README.md - Full documentation
- IMPLEMENTATION_SUMMARY.md - Technical details
- docs/k8s_troubleshooting.md - Sample documentation
- GitHub Issues - Report problems

## Success! 🎉

You're now ready to troubleshoot Kubernetes issues with AI!

Try this:
```bash
./devdebug.sh interactive
```

Then ask:
```
You: My pod keeps restarting
DevDebug: [Provides detailed analysis and solution]

You: Generate a Python script to check pod health
DevDebug: [Generates working Python code]

You: exit
```

Happy troubleshooting! 🚀
