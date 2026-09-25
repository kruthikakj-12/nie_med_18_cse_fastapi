from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Enterprise IT service Desk-server"}

db = {
    1: {"id": 1, "title": "computer is not on", "description": "power button is not working","category": "hardware", "status": "NEW"},
    2: {"id": 2, "title": "internet is not working", "description": "wifi problem","category": "hardware", "status": "NEW"},
}
#schemas
class TicketCreate(BaseModel):
    title :str
    description: str
    category: str
    status: str
    
class TicketResponse(TicketCreate):
    id : int


@app.get("/tickets")
def ticket_read_all():
    return list(db.values())

@app.get("/tickets/{id}")
def ticket_read_all_id(id : int):
    if id not in db:
        raise HTTPException(detail="Ticket not found", status_code=404)
        return {"error": "Ticket not found"}
    return db[id]

@app.post("/tickets", status_code=201,response_model=TicketResponse)
def ticket_create(ticket_payload : TicketCreate):
    new_id = max(db.keys(),default=0) +1
    db[new_id] = {"id":new_id,**ticket_payload.model_dump()}
    return db[new_id]

@app.put("/tickets/{id}", response_model=TicketResponse)
def ticket_update(id:int, ticket_payload: TicketCreate):
    if id not in db:
        raise HTTPException(detail="Ticket not found", status_code=404)
    db[id]=  {"id": id, **ticket_payload.model_dump()}
    return db[id]
@app.delete("/tickets/{id}")
def ticket_delete(id:int):
    if id not in db:
        raise HTTPException(detail="Ticket not found", status_code=404)
    del db[id]
    return {"message": "Ticket deleted successfully"}