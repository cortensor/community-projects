"""
Database models for Agent Auditor
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.base import Base  # Changed from backend.database


class Agent(Base):
    """Agent model - stores information about audited agents"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to audits
    audits = relationship("Audit", back_populates="agent")


class Audit(Base):
    """Audit model - stores audit results"""
    __tablename__ = "audits"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String, unique=True, index=True, nullable=False)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False)
    agent_name = Column(String, nullable=True)
    
    # Task information
    task_description = Column(Text, nullable=False)
    task_input = Column(Text, nullable=False)
    category = Column(String, default="general")
    
    # Audit results
    status = Column(String, default="pending")  # pending, running, completed, failed
    final_confidence = Column(Float, nullable=True)
    poi_similarity = Column(Float, nullable=True)
    pouw_mean_score = Column(Float, nullable=True)
    
    # Evidence storage
    ipfs_cid = Column(String, nullable=True)
    evidence_hash = Column(String, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship to agent
    agent = relationship("Agent", back_populates="audits")
