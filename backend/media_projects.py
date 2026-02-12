import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Media, Project
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from jose import jwt, JWTError

router = APIRouter()

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Dependency to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = parts[1]
        SECRET = os.getenv("JWT_SECRET", "change-this-secret")
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Schemas ---
class ProjectCreate(BaseModel):
    text: str
    title: Optional[str] = None
    link: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    text: str
    title: Optional[str]
    link: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

class MediaResponse(BaseModel):
    id: int
    type: str  # 'image' or 'video'
    url: str
    filename: str
    mime_type: Optional[str]
    size: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True

# --- Constants ---
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/webm', 'video/quicktime'}

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Projects Endpoints ---
@router.post("/user/projects", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project for the authenticated user"""
    new_project = Project(
        user_id=user.id,
        text=project.text,
        title=project.title,
        link=project.link,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return ProjectResponse(
        id=new_project.id,
        text=new_project.text,
        title=new_project.title,
        link=new_project.link,
        created_at=new_project.created_at.isoformat(),
    )

@router.get("/user/projects", response_model=List[ProjectResponse])
def get_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all projects for the authenticated user"""
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()
    return [
        ProjectResponse(
            id=p.id,
            text=p.text,
            title=p.title,
            link=p.link,
            created_at=p.created_at.isoformat(),
        )
        for p in projects
    ]

@router.delete("/user/projects/{project_id}")
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project by ID (must belong to authenticated user)"""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

# --- Media Endpoints ---
@router.post("/user/media", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload image or video for the authenticated user"""
    
    # Validate file type
    if file.content_type not in (ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES):
        raise HTTPException(status_code=400, detail="Unsupported file type. Only images and videos allowed.")
    
    # Determine media type
    if file.content_type in ALLOWED_IMAGE_TYPES:
        media_type = "image"
    else:
        media_type = "video"
    
    # Read file and check size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is 100 MB.")
    
    # Create safe filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    unique_filename = f"{user.id}_{uuid.uuid4()}.{ext}"
    user_upload_dir = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    file_path = os.path.join(user_upload_dir, unique_filename)
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # Create URL (relative path for backend serving)
    url = f"/uploads/{user.id}/{unique_filename}"
    
    # Save to database
    media_record = Media(
        user_id=user.id,
        type=media_type,
        filename=unique_filename,
        url=url,
        mime_type=file.content_type,
        size=file_size,
    )
    db.add(media_record)
    db.commit()
    db.refresh(media_record)
    
    return MediaResponse(
        id=media_record.id,
        type=media_record.type,
        url=media_record.url,
        filename=media_record.filename,
        mime_type=media_record.mime_type,
        size=media_record.size,
        created_at=media_record.created_at.isoformat(),
    )

@router.get("/user/media", response_model=List[MediaResponse])
def get_media(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all media for the authenticated user"""
    media_items = db.query(Media).filter(Media.user_id == user.id).order_by(Media.created_at.desc()).all()
    return [
        MediaResponse(
            id=m.id,
            type=m.type,
            url=m.url,
            filename=m.filename,
            mime_type=m.mime_type,
            size=m.size,
            created_at=m.created_at.isoformat(),
        )
        for m in media_items
    ]

@router.delete("/user/media/{media_id}")
def delete_media(
    media_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete media by ID (must belong to authenticated user)"""
    media = db.query(Media).filter(Media.id == media_id, Media.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Delete file from disk
    file_path = os.path.join(".", media.url.lstrip('/'))
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    db.delete(media)
    db.commit()
    
    return {"message": "Media deleted successfully"}

# --- Bulk migrate endpoint (for localStorage migration) ---
@router.post("/user/migrate")
def migrate_user_data(
    projects: List[ProjectCreate] = [],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Migrate projects from localStorage (media migration handled via file uploads)"""
    
    created_count = 0
    for proj in projects:
        new_project = Project(
            user_id=user.id,
            text=proj.text,
            title=proj.title,
            link=proj.link,
        )
        db.add(new_project)
        created_count += 1
    
    db.commit()
    return {"message": f"Migrated {created_count} projects successfully"}

