from pathlib import Path
import shutil
import uuid
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, get_db
from .models import User, File
from .security import hash_password, verify_password, create_access_token, decode_token
app = FastAPI(title="File Vault API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


security = HTTPBearer(auto_error=True)




STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    print("AUTH HEADER TOKEN:", credentials.credentials)

    token = credentials.credentials

    try:
        email = decode_token(token)
        print("DECODED EMAIL:", email)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "created": True,
        "user_id": user.id,
        "email": user.email
    }


@app.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }


@app.post("/files/upload")
def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not uploaded_file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    file_id = str(uuid.uuid4())
    suffix = Path(uploaded_file.filename).suffix
    stored_filename = f"{file_id}{suffix}"
    destination = STORAGE_DIR / stored_filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    size_bytes = destination.stat().st_size
    content_type = uploaded_file.content_type or "application/octet-stream"

    file_record = File(
        owner_user_id=current_user.id,
        original_filename=uploaded_file.filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_provider="local",
        storage_key=str(destination)
    )

    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    return {
        "id": file_record.id,
        "original_filename": file_record.original_filename,
        "size_bytes": file_record.size_bytes,
        "content_type": file_record.content_type
    }


@app.get("/files")
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    files = (
        db.query(File)
        .filter(File.owner_user_id == current_user.id)
        .order_by(File.created_at.desc())
        .all()
    )

    return [
        {
            "id": f.id,
            "original_filename": f.original_filename,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at.isoformat()
        }
        for f in files
    ]


@app.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file_record = (
        db.query(File)
        .filter(File.id == file_id, File.owner_user_id == current_user.id)
        .first()
    )

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_record.storage_key)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file missing on disk")

    return FileResponse(
        path=file_path,
        media_type=file_record.content_type,
        filename=file_record.original_filename
    )

    app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)