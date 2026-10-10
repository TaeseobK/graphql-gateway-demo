"""GraphQL schema. Every field declares the permission it needs; resolvers call downstream services."""
import strawberry
from strawberry.permission import PermissionExtension
from strawberry.types import Info

from .auth import HasPermission
from .events import publish

EVENT_STREAM = "employee.events"


@strawberry.type
class Employee:
    id: int
    name: str
    department: str


@strawberry.type
class Query:
    @strawberry.field(extensions=[PermissionExtension(permissions=[HasPermission("employee.read")])])
    async def employees(self, info: Info, department: str | None = None) -> list[Employee]:
        params = {"department": department} if department else None
        response = await info.context["upstream"].get("/employees", params=params)
        response.raise_for_status()
        return [Employee(**item) for item in response.json()]


@strawberry.type
class Mutation:
    @strawberry.mutation(extensions=[PermissionExtension(permissions=[HasPermission("employee.write")])])
    async def add_employee(self, info: Info, name: str, department: str) -> Employee:
        response = await info.context["upstream"].post(
            "/employees", json={"name": name, "department": department}
        )
        response.raise_for_status()
        employee = response.json()
        await publish(info.context["redis"], EVENT_STREAM, {"type": "employee.created", **employee})
        return Employee(**employee)


schema = strawberry.Schema(query=Query, mutation=Mutation)
