from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from fastapi.encoders import jsonable_encoder
from models.database import engine
from models.database import Base,SessionLocal
from models.message import Message
from models.user import User
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker,Session
from pydantic import BaseModel
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json



SQLALCHEMY_DATABASE_URL = "sqlite:///database.db"
User.metadata.create_all(bind=engine)
Message.metadata.create_all(bind=engine)

app = FastAPI()
# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# Dependency
def get_db():
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
       
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    
    await manager.connect(websocket)
    db = SessionLocal()

    user = db.query(User).filter(User.id == client_id).first()
    user.online = True
    db.commit()
    db.refresh(user)

    now = datetime.now()
    current_time = now.strftime("%H:%M")
    try:
        while True:
            data = await websocket.receive_text()  
            message = {"time":current_time,"clientId":client_id,"message":data}
            if data != "":
                await send_message(data,client_id)
               
            await manager.broadcast(json.dumps(message))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
       
        db = SessionLocal()
        user = db.query(User).filter(User.id == client_id).first()
        user.online = False
        db.commit()
        db.refresh(user)
        message = {"time":current_time,"clientId":client_id,"message":"Offline"}
        await manager.broadcast(json.dumps(message))



        
# Registeration
class UserCreate(BaseModel):
    email:str
    username: str
    password: str

class LoginForm(BaseModel):
    email: str
    password: str

class MessageCreate(BaseModel):
    user_id: int
    content: str





@app.post("/register")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = pwd_context.hash(user.password)
    db_user = User(email=user.email,username=user.username, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Return JSON response with status code 201
    return JSONResponse(status_code=201, content={"message": "User created successfully"})


@app.post("/login")
async def login(login_data: LoginForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # You can return any data you need here, for simplicity let's return a success message
    return JSONResponse(status_code=200, content={"message": "Login successful","user":user.id})



# Message creation endpoint

async def send_message(message,client_id):
    # Check if the user exists
    db = SessionLocal()
   
    user = db.query(User).filter(User.id == client_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create the message
    db_message = Message(sender_id=client_id, content=message)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return JSONResponse(status_code=201, content={"message": "Message inserted successfully", "new_message": db_message.content})

    
@app.get("/messages")
async def get_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).all()
    messages_data = []
    for message in messages:
        message_dict = {
            "id": message.id,
            "sender_id": message.sender_id,
            "sender":message.sender.username,
            "online":message.sender.online,
            "content": message.content,
            # Add more attributes as needed
        }
        messages_data.append(message_dict)

    
    return JSONResponse(status_code=200, content={"data": messages_data})


@app.delete("/message/{message_id}")
async def delete_message(message_id:int,db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    # Delete the message
    db.delete(message)
    db.commit()
    
    return JSONResponse(status_code=200, content={"message": "Message Deleted Successfully"})



@app.get("/")
async def root():
    return {"message": "Hello World"}



if __name__ == "__main__":
  
    Base.metadata.create_all(bind=engine)

    uvicorn.run(app, host="127.0.0.1", port=8000)
