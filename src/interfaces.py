"""Core interfaces for DevDebug AI agents"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AgentType(Enum):
    """Types of agents in the system"""
    DOCUMENT = "document"
    EXECUTION = "execution"
    LLM = "llm"
    MONITORING = "monitoring"


@dataclass
class AgentRequest:
    """Standard request format for all agents"""
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    priority: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate request after initialization"""
        if not self.query:
            raise ValueError("Query cannot be empty")


@dataclass
class AgentResponse:
    """Standard response format from agents"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_type: Optional[AgentType] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent with configuration
        
        Args:
            config: Configuration dictionary for the agent
        """
        self.config = config
        self.agent_type = None
        self.initialized = False
        self.initialize()
        self.initialized = True
    
    @abstractmethod
    def initialize(self):
        """Initialize the agent with configuration"""
        pass
    
    @abstractmethod
    def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a request and return response
        
        Args:
            request: AgentRequest object containing query and context
            
        Returns:
            AgentResponse with results or error
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if agent is healthy and operational
        
        Returns:
            True if agent is healthy, False otherwise
        """
        pass
    
    def cleanup(self):
        """Cleanup resources - override if needed"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
        return False


class AgentError(Exception):
    """Base exception for agent errors"""
    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails"""
    pass


class AgentProcessingError(AgentError):
    """Raised when agent processing fails"""
    pass
