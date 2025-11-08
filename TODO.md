# 📝 DevDebug AI - TODO List

**Last Updated:** November 8, 2025

---

## 🔴 High Priority (Before Demo)

### 1. 3-Tier Query Classification System
**Status:** ✅ COMPLETED (Nov 8, 2025)  
**Effort:** 2 hours  
**File:** `core/orchestrator.py`

**Implementation:**
Replaced 2-tier system (action vs diagnostic) with 3-tier classification:

**Tier 1: Informational (Fast Path - 5-10 sec)**
- Keywords: who, which, what, show, list, get, describe, check, display, print, view
- Flow: Generate commands → Execute → LLM summarizes → Direct answer
- Examples: "list pods", "show deployments", "who scheduled pod X"
- Method: `_process_informational_query()`

**Tier 2: Troubleshooting (Full Investigation - 30-60 sec)**
- Keywords: debug, troubleshoot, diagnose, investigate, why, how, fix, resolve, failing, error, broken
- Flow: RAG → Iterative investigation → Root cause analysis → Solution
- Examples: "debug failing pods", "why is pod crashing", "fix deployment error"
- Method: `_process_troubleshooting_query()` (renamed from `_process_diagnostic_query`)

**Tier 3: Action (Execute Commands - 10-15 sec)**
- Keywords: delete, create, scale, restart, patch, apply, edit
- Flow: Generate commands → Confirm → Execute → Summary
- Examples: "delete pods", "scale deployment to 3", "restart pods"
- Method: `_process_action_query()`

**Priority Logic:**
1. Check informational keywords first
2. If informational + troubleshooting words → prefer troubleshooting
3. Check troubleshooting keywords
4. Check action keywords
5. Default to informational (safer)

**Benefits:**
- ✅ Simple queries now take 5-10 sec instead of 30-60 sec
- ✅ "list pods" no longer runs full investigation
- ✅ Better user experience for 80% of queries
- ✅ Reduced LLM token usage for simple queries

**Test Results:**
```python
# Verified on Linux server
"list pods" → informational → Fast ✅
"show deployments" → informational → Fast ✅
"who scheduled pod X" → informational → Fast ✅
"debug failing pods" → troubleshooting → Full investigation ✅
"why is pod crashing" → troubleshooting → Full investigation ✅
"delete pods" → action → Execute ✅
```

---

## 🟡 Medium Priority (Quality Improvements)

### 2. Fix Shell Injection Vulnerability
**Status:** Pending  
**Effort:** 30 minutes  
**File:** `agents/execution_agent.py`

**Problem:**
Using `shell=True` in subprocess with user input is a security risk.

**Solution:**
```python
import shlex

# Replace:
subprocess.run(command, shell=True, ...)

# With:
subprocess.run(shlex.split(command), shell=False, ...)
```

---

### 3. Add Input Validation
**Status:** Pending  
**Effort:** 1 hour  
**File:** `integrations/rest_api.py`

**Problem:**
No validation on user inputs (query, namespace, pod_name).

**Solution:**
Add Pydantic validators to QueryRequest model.

---

### 4. Replace print() with Logging
**Status:** Pending  
**Effort:** 2 hours  
**Files:** All Python files

**Problem:**
All output uses print() instead of proper logging framework.

**Solution:**
```python
import logging
logger = logging.getLogger(__name__)

# Replace print() with:
logger.info("message")
logger.error("error")
```

---

### 5. Fix CORS Configuration
**Status:** Pending  
**Effort:** 15 minutes  
**File:** `integrations/rest_api.py`

**Problem:**
CORS allows all origins (`allow_origins=["*"]`).

**Solution:**
```python
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, ...)
```

---

## 🟢 Low Priority (Nice to Have)

### 6. Add Package Structure
**Status:** Pending  
**Effort:** 45 minutes  
**Create:** `pyproject.toml`

Make project installable with `pip install -e .`

---

### 7. Improve Error Messages
**Status:** Pending  
**Effort:** 1 hour  
**Files:** All agents

Add custom exception types instead of generic Exception.

---

### 8. Add Unit Tests
**Status:** Pending  
**Effort:** 3 hours  
**File:** `tests/test_components.py`

Rewrite with pytest and proper mocking.

---

## 📊 Progress Tracking

**Total Pending:** 7 tasks  
**Before Demo (Critical):** 1 task  
**Quality Improvements:** 4 tasks  
**Nice to Have:** 2 tasks  

---

**Focus:** Complete high priority items first, then tackle quality improvements before demo.
