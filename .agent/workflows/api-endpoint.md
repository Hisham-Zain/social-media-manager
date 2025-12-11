---
description: Add a new REST API endpoint to the project
---

# API Endpoint Workflow

Use this workflow when adding a new REST API endpoint.

## Steps

1. **Define the endpoint spec**:
   - HTTP method (GET, POST, PUT, DELETE)
   - URL path (e.g., `/api/v1/users`)
   - Request body schema (if applicable)
   - Response schema
   - Authentication requirements

2. **Create the route handler**:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class RequestModel(BaseModel):
    field: str

class ResponseModel(BaseModel):
    id: int
    field: str

@router.post("/endpoint", response_model=ResponseModel)
async def create_item(data: RequestModel) -> ResponseModel:
    """Create a new item."""
    # Implementation here
    return ResponseModel(id=1, field=data.field)
```

3. **Register the router** in the main app:
```python
app.include_router(router, prefix="/api/v1", tags=["items"])
```

4. **Create integration tests** in `tests/integration/`:
```python
def test_create_item(client):
    response = client.post("/api/v1/endpoint", json={"field": "value"})
    assert response.status_code == 200
    assert response.json()["field"] == "value"
```

// turbo
5. **Run tests**:
```bash
pytest tests/ -v -k "test_endpoint"
```

6. **Update API documentation** if not auto-generated.

7. **Commit**:
```bash
git commit -m "feat(api): add /endpoint route"
```
