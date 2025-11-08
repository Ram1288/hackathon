# 🎯 DevDebug AI - Project Scope

**What:** AI-powered Kubernetes troubleshooting assistant  
**Type:** Hackathon Prototype  
**Status:** Active Development

---

## Core System

### Architecture
- **7 Specialized Agents** working together via orchestrator
- **Iterative Investigation** (up to 5 rounds) until root cause found
- **Pattern Recognition** prevents AI hallucination
- **Security Validation** on all commands before execution

### User Flow
```
User Query → Intent Detection → Action Mode OR Diagnostic Mode
                                      ↓                ↓
                              Execute Commands    Investigation
                                                  (5 iterations max)
                                      ↓                ↓
                                   Summary        Solution

Intent Detection:
- "delete pods" → Action Mode (executes commands)
- "debug pods" → Diagnostic Mode (investigates & advises)
```

---

## Must-Have Features

### ✅ Dual Mode Operation
- [ ] **Action Mode**: Execute commands when user says "delete", "create", "scale", etc.
- [ ] **Diagnostic Mode**: Investigate & troubleshoot when user says "debug", "why", "check", etc.
- [ ] Intent detection works correctly
- [ ] Security validates all commands before execution

### ✅ Investigation System
- [ ] Detects common K8s errors (CrashLoopBackOff, OOMKilled, ImagePullBackOff, etc.)
- [ ] Pattern recognition in iteration 1 (no LLM hallucination)
- [ ] Iterates up to 5 times until confident (>70%)
- [ ] Final solution respects investigation findings

### ✅ Command Execution
- [ ] Executes kubectl commands safely (no shell injection)
- [ ] Security validation before execution
- [ ] Configurable permissions (read-only, allow_delete, allow_create)
- [ ] Logs all commands for audit

### ✅ AI Integration
- [ ] Uses Ollama + Llama 3.1:8b
- [ ] Generates diagnostic commands
- [ ] Analyzes results and provides solutions
- [ ] Graceful fallback if Ollama unavailable

### ✅ Interfaces
- [ ] CLI: health check, single query, interactive mode
- [ ] API: POST /query, GET /health, Swagger docs
- [ ] Both work without errors

### ✅ Configuration
- [ ] All settings in config.yaml
- [ ] Agent configurations separated
- [ ] Security settings enforced
- [ ] CORS properly configured (not *)

---

## Error Patterns to Detect

```yaml
OOMKilled:          95% confidence → "Container exceeded memory limit"
CrashLoopBackOff:   90% confidence → "Application crashing on startup"
ImagePullBackOff:   95% confidence → "Cannot pull container image"
CreateContainerConfigError: 90% confidence → "Configuration error"
Pending:            85% confidence → "Resource/scheduling issue"
```

---

## Real-World Test Cases

### Test 1: Diagnostic Mode - OOMKilled Pod
**Query:** `"debug the pods which are not running"`  
**Mode:** Diagnostic (investigate)  
**Expected:**
1. Iteration 1: Find non-running pods
2. Iteration 2: kubectl describe shows "OOMKilled"
3. Pattern Recognition: 95% confidence
4. Solution: "Increase memory limit from 128Mi to 256Mi"
5. ❌ Must NOT say "lack of resources" if actual error is OOMKilled

### Test 2: Diagnostic Mode - Missing ConfigMap
**Query:** `"grafana-operator pods not starting"`  
**Mode:** Diagnostic (investigate)  
**Expected:**
1. Pattern detects: CreateContainerConfigError
2. Root cause: Missing ConfigMap reference
3. Solution: Create required ConfigMap
4. ❌ Must NOT hallucinate other causes

### Test 3: Action Mode - Delete Pods
**Query:** `"delete the pods which are not running"`  
**Mode:** Action (execute commands)  
**Expected:**
1. LLM generates: kubectl get pods (find non-running)
2. LLM generates: kubectl delete pods <names>
3. Shows commands before execution
4. Executes commands via ExecutionAgent
5. Returns summary of what was deleted

### Test 4: Security Validation
**Query:** `"delete all pods and rm -rf /"`  
**Mode:** Action (attempted)  
**Expected:**
1. Security agent blocks dangerous "rm -rf" command
2. Returns error message
3. ❌ Must NOT execute any part of the command

---

## Not Implementing (Out of Scope)

**For Hackathon:**
- ❌ Multiple LLM providers - Ollama only
- ❌ Real vector database - Keyword search OK
- ❌ Web UI - CLI/API only
- ❌ Multi-cluster - Single cluster
- ❌ Database persistence - Memory only
- ❌ Complex authentication - Optional API key
- ❌ Production monitoring - Basic logs
- ❌ CI/CD pipeline - Manual only

---

## Definition of Done

### Code Quality ✓
- [ ] No sys.path hacks in imports
- [ ] No shell=True with user input
- [ ] Input validation on all endpoints
- [ ] Proper exception handling
- [ ] Config structure matches code

### Functionality ✓
- [ ] All 7 agents initialize
- [ ] Pattern recognition works
- [ ] Investigation iterates correctly
- [ ] CLI and API both work
- [ ] Security blocks bad commands
- [ ] Real K8s test passes

### Documentation ✓
- [ ] Setup takes <5 minutes
- [ ] QUICKSTART works
- [ ] Claims are honest (prototype)
- [ ] Demo script ready

### Testing ✓
- [ ] Health check passes
- [ ] Test cases 1-3 work correctly
- [ ] Ollama fallback works
- [ ] No crashes on normal use

---

## Quick Validation Checklist

**Can you demo this in 3 minutes?**
- [ ] `python integrations/standalone.py health` → All agents OK
- [ ] **Diagnostic Mode:** `--query "debug pods not running"` → Investigation + solution
- [ ] **Action Mode:** `--query "delete pods not running"` → Generates + executes commands
- [ ] **Security:** Try `--query "delete all; rm -rf /"` → Blocks dangerous command
- [ ] **API:** `curl -X POST http://localhost:8000/query ...` → JSON response

**If all 5 work → Project is DONE ✅**

---

**Last Updated:** November 8, 2025
