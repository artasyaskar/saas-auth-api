"""Workflow Automation API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.services.workflow import WorkflowService, WorkflowStatus, TaskStatus
from app.core.security import get_current_user

router = APIRouter(prefix="/workflows", tags=["workflows"])


class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    definition: dict
    variables: Optional[dict] = None


class ExecuteWorkflowRequest(BaseModel):
    input_data: Optional[dict] = None


@router.post("/")
async def create_workflow(request: CreateWorkflowRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = WorkflowService(db)
    workflow_id = service.create_workflow(
        name=request.name,
        description=request.description,
        definition=request.definition,
        variables=request.variables,
        created_by=current_user.id
    )
    return {"workflow_id": workflow_id}


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: int, request: ExecuteWorkflowRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = WorkflowService(db)
    execution_id = service.execute_workflow(
        workflow_id=workflow_id,
        initiator_id=current_user.id,
        input_data=request.input_data
    )
    return {"execution_id": execution_id}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = WorkflowService(db)
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/")
async def list_workflows(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = WorkflowService(db)
    return service.list_workflows()


@router.get("/{workflow_id}/analytics")
async def get_workflow_analytics(workflow_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = WorkflowService(db)
    return service.get_workflow_analytics(workflow_id)
