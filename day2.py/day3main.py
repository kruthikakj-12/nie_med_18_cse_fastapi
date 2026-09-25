from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
import jwt

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone


app = FastAPI()


# =========================
# MongoDB Configuration
# =========================

URL = "mongodb://127.0.0.1:27017"

client = MongoClient(URL)

db = client["richest_tickets_db"]

ticket_collection = db["tickets"]
user_collection = db["users"]


# =========================
# Security Configuration
# =========================

SECRET_KEY = "ITServiceDesksecuritykey-ChangeThis"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

password_hash = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================
# Pydantic Models
# =========================

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    status: str


class TicketResponse(TicketCreate):
    id: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# =========================
# Helper Functions
# =========================

def ticket_helper(ticket):
    return {
        "id": str(ticket["_id"]),
        "title": ticket["title"],
        "description": ticket["description"],
        "category": ticket["category"],
        "status": ticket["status"]
    }


def user_helper(user):
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"]
    }


# =========================
# JWT Token
# =========================

def create_token(username: str, role: int):

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "role": role,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# =========================
# Get Current User
# =========================

def get_current_user(
    token: str = Depends(oauth2_scheme)
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if username is None or role is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = user_collection.find_one(
        {"username": username}
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "username": username,
        "role": role
    }


# =========================
# Role Checking
# =========================

def require_role(*allowed_roles):

    def check_role(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] not in allowed_roles:

            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        return current_user

    return check_role


# =========================
# USER APIs
# =========================


# Create User
@app.post("/user", status_code=201)
def create_user(user: UserCreate):

    queried_user = user_collection.find_one(
        {"username": user.username}
    )

    if queried_user:

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    hashed_password = password_hash.hash(
        user.password
    )

    user_data = {
        "username": user.username,
        "password": hashed_password,
        "role": user.role
    }

    result = user_collection.insert_one(
        user_data
    )

    new_user = user_collection.find_one(
        {"_id": result.inserted_id}
    )

    return user_helper(new_user)


# Login
@app.post(
    "/login",
    response_model=TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    user = user_collection.find_one(
        {"username": form_data.username}
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not password_hash.verify(
        form_data.password,
        user["password"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    token = create_token(
        user["username"],
        user["role"]
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# =========================
# TICKET APIs
# =========================


# Create Ticket
@app.post(
    "/tickets",
    status_code=201,
    response_model=TicketResponse
)
def ticket_create(
    payload: TicketCreate,
    current_user=Depends(
        require_role(1, 2)
    )
):

    ticket_dict = payload.model_dump()

    result = ticket_collection.insert_one(
        ticket_dict
    )

    new_ticket = ticket_collection.find_one(
        {"_id": result.inserted_id}
    )

    return ticket_helper(new_ticket)


# Get Ticket By ID
@app.get(
    "/tickets/{id}",
    response_model=TicketResponse
)
def ticket_read_by_id(
    id: str,
    current_user=Depends(
        require_role(1, 2, 3, 4)
    )
):

    if not ObjectId.is_valid(id):

        raise HTTPException(
            status_code=400,
            detail="Invalid ticket ID"
        )

    ticket_result = ticket_collection.find_one(
        {"_id": ObjectId(id)}
    )

    if not ticket_result:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return ticket_helper(ticket_result)


# Update Ticket
@app.put(
    "/tickets/{id}",
    response_model=TicketResponse
)
def ticket_update(
    id: str,
    payload: TicketCreate,
    current_user=Depends(
        require_role(1, 2, 3, 4)
    )
):

    if not ObjectId.is_valid(id):

        raise HTTPException(
            status_code=400,
            detail="Invalid ticket ID"
        )

    ticket_dict = payload.model_dump()

    result = ticket_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": ticket_dict}
    )

    if result.matched_count == 0:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    new_ticket = ticket_collection.find_one(
        {"_id": ObjectId(id)}
    )

    return ticket_helper(new_ticket)


# Delete Ticket
@app.delete("/tickets/{id}")
def ticket_delete(
    id: str,
    current_user=Depends(
        require_role(4)
    )
):

    if not ObjectId.is_valid(id):

        raise HTTPException(
            status_code=400,
            detail="Invalid ticket ID"
        )

    result = ticket_collection.delete_one(
        {"_id": ObjectId(id)}
    )

    if result.deleted_count == 0:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return {
        "message": "Ticket deleted successfully"
    }


# =========================
# Root API
# =========================

@app.get("/")
def home():

    return {
        "message": "IT Service Desk API is running"
    }