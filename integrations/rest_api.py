"""REST API interface for DevDebug AI"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import yaml
from pathlib import Path
import sys

from core.orchestrator import DevDebugOrchestrator


# Initialize FastAPI app
app = FastAPI(
    title="DevDebug AI API",
    description="Intelligent Kubernetes Troubleshooting API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None


# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for troubleshooting queries"""
    query: str = Field(..., description="Issue description or question")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    namespace: str = Field("default", description="Kubernetes namespace")
    pod_name: Optional[str] = Field(None, description="Specific pod name")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "My pod is in CrashLoopBackOff state",
                "namespace": "production",
                "pod_name": "api-server-abc123"
            }
        }


class QueryResponse(BaseModel):
    """Response model for troubleshooting queries"""
    session_id: str
    query: str
    namespace: str
    solution: str
    diagnostics: Dict[str, Any]
    documentation: List[Dict[str, Any]]
    code_examples: Dict[str, List[str]]
    k8s_patterns: List[Dict[str, Any]]
    timestamp: float
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for health check"""
    orchestrator: bool
    overall_healthy: bool
    timestamp: str
    agents: Dict[str, Any]


class SessionHistoryResponse(BaseModel):
    """Response model for session history"""
    session_id: str
    history: List[Dict[str, Any]]
    count: int


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    
    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            # Use default config
            config = {
                'document_agent': {'doc_dir': './docs'},
                'execution_agent': {'ssh_enabled': False},
                'llm_agent': {
                    'ollama_url': 'http://localhost:11434',
                    'model': 'llama3.1:8b'
                },
                'orchestrator': {
                    'max_session_history': 100,
                    'session_timeout': 3600
                }
            }
        
        orchestrator = DevDebugOrchestrator(config)
        print("✓ DevDebug AI API ready")
        
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global orchestrator
    if orchestrator:
        orchestrator.shutdown()


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "DevDebug AI API",
        "version": "1.0.0",
        "description": "Intelligent Kubernetes Troubleshooting Assistant",
        "endpoints": {
            "POST /query": "Submit troubleshooting query",
            "GET /health": "Check system health",
            "GET /session/{session_id}": "Get session history",
            "DELETE /session/{session_id}": "Clear session",
            "GET /agents": "Get agent information"
        }
    }


@app.post("/query", response_model=QueryResponse, tags=["Troubleshooting"])
async def process_query(request: QueryRequest):
    """
    Process a troubleshooting query
    
    This endpoint:
    1. Searches documentation for relevant information
    2. Runs diagnostics on the Kubernetes cluster
    3. Generates an intelligent solution using LLM
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = orchestrator.process_query(
            query=request.query,
            session_id=request.session_id,
            namespace=request.namespace,
            pod_name=request.pod_name
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check health of all agents
    
    Returns the operational status of:
    - Document Agent (RAG)
    - Execution Agent (K8s diagnostics)
    - LLM Agent (Solution generation)
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        health_status = orchestrator.health_check()
        return HealthResponse(**health_status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}", response_model=SessionHistoryResponse, tags=["Session"])
async def get_session_history(session_id: str):
    """
    Get history for a specific session
    
    Returns all previous queries and solutions in the session
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        history = orchestrator.get_session_history(session_id)
        
        return SessionHistoryResponse(
            session_id=session_id,
            history=history,
            count=len(history)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}", tags=["Session"])
async def clear_session(session_id: str):
    """Clear a specific session"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        success = orchestrator.clear_session(session_id)
        
        if success:
            return {"message": f"Session {session_id} cleared", "success": True}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", tags=["System"])
async def get_agents():
    """Get information about all agents"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        agent_info = orchestrator.get_agent_info()
        return {
            "agents": agent_info,
            "count": len(agent_info)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cleanup", tags=["System"])
async def cleanup_sessions(background_tasks: BackgroundTasks):
    """Cleanup old sessions (runs in background)"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        def cleanup_task():
            count = orchestrator.cleanup_old_sessions()
            print(f"Cleaned up {count} old sessions")
        
        background_tasks.add_task(cleanup_task)
        return {"message": "Cleanup task scheduled"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Example usage for testing
@app.get("/examples", tags=["General"])
async def get_examples():
    """Get example queries"""
    return {
        "examples": [
            {
                "query": "My pod is in CrashLoopBackOff",
                "namespace": "default"
            },
            {
                "query": "ImagePullBackOff error on my deployment",
                "namespace": "production",
                "pod_name": "api-server-xyz"
            },
            {
                "query": "Pod keeps getting OOMKilled",
                "namespace": "default"
            },
            {
                "query": "Show me all failing pods in production",
                "namespace": "production"
            },
            {
                "query": "Generate a Python script to list all pods with resource limits",
                "namespace": "default"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
