# 📝 DevDebug AI - TODO List

**Last Updated:** November 8, 2025

---

## 🔴 High Priority (Before Demo)

### 1. Improve Intent Detection Logic
**Status:** Pending  
**Effort:** 30 minutes  
**File:** `core/orchestrator.py` - `_determine_query_intent()`

**Problem:**
- Diagnostic keywords are defined but never checked
- Only action keywords are validated
- Ambiguous queries (e.g., "delete and debug") not handled intelligently

**Solution Options:**
- ✅ **Option 1 (Recommended):** Position-based priority
  - Check both action and diagnostic keywords
  - If both present, use whichever comes first in query
  - Example: "delete and debug" → action (delete first)
  - Example: "debug then delete" → diagnostic (debug first)

- Option 2: Strict mode
  - Reject queries with both action and diagnostic keywords
  - Force user to be explicit

- Option 3: Simple fix
  - Check action keywords first (priority)
  - Then check diagnostic keywords
  - Default to diagnostic if neither

**Test Cases After Fix:**
```python
assert _determine_query_intent("delete pods") == "action"
assert _determine_query_intent("debug pods") == "diagnostic"
assert _determine_query_intent("show pods") == "diagnostic"
assert _determine_query_intent("delete and debug") == "action"  # delete first
assert _determine_query_intent("debug then delete") == "diagnostic"  # debug first
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
