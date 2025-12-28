"""
FastAPI application - REST API for Cortensor Agent Auditor
"""
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.config import settings
from backend.database import init_db, get_db_session
from backend.orchestrator import orchestrator
from backend.models import Agent, Audit

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level, "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cortensor Agent Auditor API",
    description="Trust & verification layer for AI agents using PoI and PoUW",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
origins = settings.cors_origins.split(",") if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== REQUEST/RESPONSE MODELS ====================
class AuditRequest(BaseModel):
    agent_id: str = Field(..., description="Unique identifier for the agent", min_length=1)
    agent_name: Optional[str] = Field(None, description="Human-readable agent name")
    task_description: str = Field(..., description="Description of the task", min_length=1)
    task_input: str = Field(..., description="The input/prompt for the agent", min_length=1)
    category: Optional[str] = Field("general", description="Task category")


class AuditResponse(BaseModel):
    audit_id: str
    agent_id: str
    status: str
    confidence_score: Optional[float] = None
    poi_similarity: Optional[float] = None
    pouw_mean_score: Optional[float] = None
    ipfs_hash: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


class AgentStats(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None
    total_audits: int = 0
    avg_confidence: float = 0.0
    avg_poi_similarity: float = 0.0
    avg_pouw_score: float = 0.0
    last_audit_time: Optional[str] = None


class DashboardStats(BaseModel):
    total_audits: int
    avg_confidence: float
    successful_audits: int
    failed_audits: int
    recent_audits: List[dict] = []


class AuditListItem(BaseModel):
    audit_id: str
    agent_id: str
    agent_name: Optional[str] = None
    timestamp: str
    status: str
    confidence_score: float = 0.0
    poi_similarity: float = 0.0
    pouw_score: float = 0.0  # Changed from pouw_mean_score
    ipfs_hash: Optional[str] = None


class AuditListResponse(BaseModel):
    total: int
    audits: List[AuditListItem]
# =====================================================


# ==================== STARTUP/SHUTDOWN ====================
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting Cortensor Agent Auditor API...")
    
    try:
        # Initialize database
        init_db()
        logger.info("✅ Database initialized")
        
        # Log configuration
        logger.info(f"📊 Cortensor Session: {settings.cortensor_session_id}")
        logger.info(f"🔧 PoI threshold: {settings.poi_similarity_threshold}")
        logger.info(f"🔧 PoUW validators: {settings.pouw_num_validators}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Cortensor Agent Auditor API...")
# =====================================================


# ==================== ROOT ROUTES ====================
@app.get("/")
async def root():
    """Health check - root endpoint"""
    return {
        "service": "Cortensor Agent Auditor",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health(db: Session = Depends(get_db_session)):
    """Detailed health check"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "cortensor_session": settings.cortensor_session_id,
        "timestamp": datetime.utcnow().isoformat()
    }
# =====================================================


# ==================== DASHBOARD STATS ====================
@app.get("/api/v1/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db_session)):
    """Get overall dashboard statistics"""
    try:
        total_audits = db.query(Audit).count()
        successful_audits = db.query(Audit).filter(Audit.status == "completed").count()
        failed_audits = db.query(Audit).filter(Audit.status == "failed").count()
        
        avg_confidence = db.query(func.avg(Audit.final_confidence))\
            .filter(Audit.status == "completed")\
            .scalar() or 0.0
        
        # Get recent audits
        recent = db.query(Audit)\
            .order_by(desc(Audit.timestamp))\
            .limit(5)\
            .all()
        
        recent_audits = [
            {
                "audit_id": audit.audit_id,
                "agent_id": audit.agent_id,
                "timestamp": audit.timestamp.isoformat(),
                "status": audit.status,
                "confidence_score": audit.final_confidence
            }
            for audit in recent
        ]
        
        return DashboardStats(
            total_audits=total_audits,
            avg_confidence=float(avg_confidence),
            successful_audits=successful_audits,
            failed_audits=failed_audits,
            recent_audits=recent_audits
        )
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# =====================================================


# ==================== AGENTS ====================
@app.get("/api/v1/agents", response_model=List[AgentStats])
async def get_agents(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db_session)
):
    """Get list of agents with their statistics"""
    try:
        # Get agents with audit statistics
        agents_query = db.query(
            Agent.agent_id,
            Agent.name,
            func.count(Audit.audit_id).label('total_audits'),
            func.avg(Audit.final_confidence).label('avg_confidence'),
            func.avg(Audit.poi_similarity).label('avg_poi'),
            func.avg(Audit.pouw_mean_score).label('avg_pouw'),
            func.max(Audit.timestamp).label('last_audit')
        ).outerjoin(Audit, Agent.agent_id == Audit.agent_id)\
         .group_by(Agent.agent_id, Agent.name)\
         .order_by(desc('total_audits'))\
         .limit(limit)\
         .offset(offset)
        
        results = agents_query.all()
        
        agents = []
        for row in results:
            agents.append(AgentStats(
                agent_id=row.agent_id,
                agent_name=row.name,
                total_audits=row.total_audits or 0,
                avg_confidence=float(row.avg_confidence or 0.0),
                avg_poi_similarity=float(row.avg_poi or 0.0),
                avg_pouw_score=float(row.avg_pouw or 0.0),
                last_audit_time=row.last_audit.isoformat() if row.last_audit else None
            ))
        
        return agents
        
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents/{agent_id}", response_model=AgentStats)
async def get_agent(agent_id: str, db: Session = Depends(get_db_session)):
    """Get detailed agent information and statistics"""
    try:
        # Get or create agent
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get statistics
        stats = db.query(
            func.count(Audit.audit_id).label('total_audits'),
            func.avg(Audit.final_confidence).label('avg_confidence'),
            func.avg(Audit.poi_similarity).label('avg_poi'),
            func.avg(Audit.pouw_mean_score).label('avg_pouw'),
            func.max(Audit.timestamp).label('last_audit')
        ).filter(Audit.agent_id == agent_id).first()
        
        return AgentStats(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            total_audits=stats.total_audits or 0,
            avg_confidence=float(stats.avg_confidence or 0.0),
            avg_poi_similarity=float(stats.avg_poi or 0.0),
            avg_pouw_score=float(stats.avg_pouw or 0.0),
            last_audit_time=stats.last_audit.isoformat() if stats.last_audit else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# =====================================================


# ==================== AUDITS ====================
@app.get("/api/v1/audits", response_model=AuditListResponse)
async def get_audits(
    limit: int = 10,
    offset: int = 0,
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """Get list of audits with optional filtering"""
    try:
        query = db.query(Audit)
        
        if agent_id:
            query = query.filter(Audit.agent_id == agent_id)
        
        if status:
            query = query.filter(Audit.status == status)
        
        total = query.count()
        
        audits = query.order_by(desc(Audit.timestamp))\
                     .limit(limit)\
                     .offset(offset)\
                     .all()
        
        audit_items = [
            AuditListItem(
                audit_id=audit.audit_id,
                agent_id=audit.agent_id,
                agent_name=audit.agent_name,
                timestamp=audit.timestamp.isoformat(),
                status=audit.status,
                confidence_score=audit.final_confidence,
                poi_similarity=audit.poi_similarity,
                pouw_score=audit.pouw_mean_score,
                ipfs_hash=audit.ipfs_cid
            )
            for audit in audits
        ]
        
        return AuditListResponse(total=total, audits=audit_items)
        
    except Exception as e:
        logger.error(f"Error fetching audits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/audit", response_model=AuditResponse)
async def create_audit(
    request: AuditRequest,
    db: Session = Depends(get_db_session)
):
    """Submit a new audit request"""
    logger.info(f"📝 Audit request for agent: {request.agent_id}")
    
    try:
        # Run audit through orchestrator
        result = await orchestrator.run_audit(
            agent_id=request.agent_id,
            agent_name=request.agent_name or request.agent_id,
            task_description=request.task_description,
            task_input=request.task_input,
            category=request.category or "general"
        )
        
        # Create or update agent in database
        agent = db.query(Agent).filter(Agent.agent_id == request.agent_id).first()
        if not agent:
            agent = Agent(
                agent_id=request.agent_id,
                name=request.agent_name or request.agent_id
            )
            db.add(agent)
            try:
                db.commit()
            except Exception as e:
                logger.warning(f"Agent creation failed: {e}")
                db.rollback()
        
        return AuditResponse(
            audit_id=result.get("audit_id", ""),
            agent_id=result.get("agent_id", request.agent_id),
            status=result.get("status", "failed"),
            confidence_score=result.get("confidence_score"),
            poi_similarity=result.get("poi_similarity"),
            pouw_mean_score=result.get("pouw_mean_score"),
            ipfs_hash=result.get("ipfs_cid"),
            timestamp=result.get("timestamp"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"❌ Audit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/audit/{audit_id}")
async def get_audit(audit_id: str, db: Session = Depends(get_db_session)):
    """Get detailed audit information"""
    audit = db.query(Audit).filter(Audit.audit_id == audit_id).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    return {
        "audit_id": audit.audit_id,
        "agent_id": audit.agent_id,
        "agent_name": audit.agent_name,
        "timestamp": audit.timestamp.isoformat(),
        "status": audit.status,
        "confidence_score": audit.final_confidence,
        "poi_similarity": audit.poi_similarity,
        "pouw_score": audit.pouw_mean_score,
        "ipfs_hash": audit.ipfs_cid,
        "task_description": audit.task_description,
        "task_input": audit.task_input,
        "category": audit.category
    }


@app.get("/api/v1/audit/{audit_id}/evidence")
async def get_audit_evidence(audit_id: str, db: Session = Depends(get_db_session)):
    """Retrieve full evidence bundle from IPFS"""
    audit = db.query(Audit).filter(Audit.audit_id == audit_id).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    if not audit.ipfs_cid:
        raise HTTPException(status_code=404, detail="Evidence not stored on IPFS")
    
    try:
        # Retrieve from IPFS
        from backend.engines.ipfs_client import ipfs_client
        bundle = ipfs_client.retrieve_bundle(audit.ipfs_cid)
        
        if not bundle:
            raise HTTPException(status_code=503, detail="Unable to retrieve evidence from IPFS")
        
        return bundle
        
    except Exception as e:
        logger.error(f"IPFS retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"IPFS error: {str(e)}")
# =====================================================


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
