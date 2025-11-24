# ===========================================
# Mini-GMAO - API FastAPI
# ===========================================
import os
from fastapi import FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, Column
from sqlalchemy import JSON
from datetime import date, timedelta
from typing import List, Optional

app = FastAPI(title="Mini-GMAO", version="0.1.0")

# Configuration DB - use environment variable or fallback to local
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gmao_user:gmao_password@localhost:5432/gmao_db")
engine = create_engine(DATABASE_URL)

# ==================== Modèles ====================
class Asset(SQLModel, table=True):
    __tablename__ = "assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: Optional[str] = None
    reg_number: Optional[str] = None
    purchase_dt: Optional[date] = None
    km: int = 0
    running_h: int = 0
    meta: Optional[dict] = Field(default={}, sa_column=Column(JSON))

class MaintType(SQLModel, table=True):
    __tablename__ = "maint_types"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    label: str

class MaintPlan(SQLModel, table=True):
    __tablename__ = "maint_plans"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int
    maint_type_id: int
    every_km: Optional[int] = None
    every_months: Optional[int] = None
    every_hours: Optional[int] = None
    tolerance_days: int = 30
    checklist_json: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    next_due_dt: Optional[date] = None

class MaintJob(SQLModel, table=True):
    __tablename__ = "maint_jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int
    due_dt: date
    done_dt: Optional[date] = None
    status: str = "planned"
    cost_labour: Optional[float] = 0.0
    cost_parts: Optional[float] = 0.0
    note: Optional[str] = None
    pdf_report: Optional[str] = None

# ==================== Startup ====================
@app.on_event("startup")
def on_startup():
    # Don't create tables - use existing schema
    pass

# ==================== Endpoints CRUD ====================
@app.post("/assets", tags=["Assets"])
def create_asset(asset: Asset):
    with Session(engine) as session:
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

@app.get("/assets", response_model=List[Asset], tags=["Assets"])
def list_assets():
    with Session(engine) as session:
        return session.exec(select(Asset)).all()

@app.post("/plans/{asset_id}/schedule", tags=["Plans"])
def schedule_job(asset_id: int):
    """Crée un job si aucun n'est en cours pour ce plan"""
    with Session(engine) as session:
        # Vérifie qu'aucun job 'planned' ou 'overdue' n'existe
        plan = session.get(MaintPlan, asset_id)
        if not plan:
            raise HTTPException(404, "Plan non trouvé")
        
        existing = session.exec(
            select(MaintJob).where(
                MaintJob.plan_id == asset_id, 
                MaintJob.done_dt == None
            )
        ).first()
        if existing:
            raise HTTPException(400, f"Job déjà programmé (ID {existing.id})")
        
        job = MaintJob(plan_id=asset_id, due_dt=plan.next_due_dt if plan.next_due_dt else date.today())
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

@app.put("/jobs/{job_id}/done", tags=["Jobs"])
def mark_job_done(job_id: int):
    """Marque un job comme fait et calcule la prochaine échéance"""
    with Session(engine) as session:
        job = session.get(MaintJob, job_id)
        if not job:
            raise HTTPException(404, "Job non trouvé")
        
        job.done_dt = date.today()
        job.status = "done"
        
        # Recalcule next_due_dt pour le plan
        plan = session.get(MaintPlan, job.plan_id)
        if plan and plan.every_months:
            plan.next_due_dt = date.today() + timedelta(days=plan.every_months*30)
        elif plan and plan.every_hours:
            # Si tu saisis les heures réelles, on recalcule en fonction
            plan.next_due_dt = date.today() + timedelta(days=plan.every_hours//24)
        
        session.commit()
        return job

@app.get("/alerts", tags=["Alerts"])
def get_alerts(window: int = Query(30, description="± jours autour d'aujourd'hui")):
    """Jobs à venir ou en retard, dans la fenêtre de tolérance"""
    with Session(engine) as session:
        start = date.today() - timedelta(days=window)
        end = date.today() + timedelta(days=window)
        
        # Get all pending jobs within the window
        jobs = session.exec(
            select(MaintJob).where(
                MaintJob.due_dt >= start,
                MaintJob.due_dt <= end,
                MaintJob.done_dt == None
            ).order_by(MaintJob.due_dt)
        ).all()
        
        results = []
        for job in jobs:
            plan = session.get(MaintPlan, job.plan_id)
            if plan:
                asset = session.get(Asset, plan.asset_id)
                results.append({
                    "job_id": job.id,
                    "asset_name": asset.name if asset else "Unknown",
                    "due_dt": job.due_dt,
                    "status": "overdue" if job.due_dt < date.today() else "planned"
                })
        
        return results
