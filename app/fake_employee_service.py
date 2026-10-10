"""A tiny in-memory stand-in for a downstream service, so the demo runs on its own."""
from fastapi import FastAPI
from pydantic import BaseModel


class NewEmployee(BaseModel):
    name: str
    department: str


def create_service() -> FastAPI:
    service = FastAPI(title="fake employee service")
    employees = [
        {"id": 1, "name": "Ayu", "department": "finance"},
        {"id": 2, "name": "Budi", "department": "engineering"},
    ]

    @service.get("/employees")
    async def list_employees(department: str | None = None):
        if department:
            return [e for e in employees if e["department"] == department]
        return employees

    @service.post("/employees", status_code=201)
    async def add_employee(payload: NewEmployee):
        employee = {"id": len(employees) + 1, **payload.model_dump()}
        employees.append(employee)
        return employee

    return service
