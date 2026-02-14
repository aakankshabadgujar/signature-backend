from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import shutil, os

from database import Base, engine, SessionLocal
from models import User, Document
from auth import hash_password, verify_password, create_access_token, get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://signature-frontend-one.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SIGNED_DIR = os.path.join(BASE_DIR, "signed")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNED_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UserCreate(BaseModel):
    email: str
    password: str

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        email=user.email,
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()

    return {"message": "User created"}

@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_access_token({"sub": db_user.email})

    return {"access_token": token}


@app.post("/upload")
def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    path = f"{UPLOAD_DIR}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    db.add(Document(
    filename=file.filename,
    filepath=path,
    status="pending",
    user_id=current_user.id
))

    db.commit()
    return {"msg": "Uploaded"}

@app.get("/documents")
def list_docs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Document).filter(Document.user_id == current_user.id).all()

@app.post("/sign/{doc_id}")
def sign_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    doc.status = "signed"
    db.commit()

    return {"message": "Signed"}




@app.get("/download/{doc_id}")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(
        path=doc.filepath,
        filename=doc.filename,
        media_type='application/pdf'
    )

@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }
