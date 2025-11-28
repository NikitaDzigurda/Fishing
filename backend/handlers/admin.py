from backend.dependencies import get_current_user, get_import_service, require_role
from fastapi.routing import APIRouter
from fastapi import Depends, HTTPException, UploadFile

from backend.models import User
from backend.service.importing import ImportService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/import", dependencies=[Depends(require_role(["admin"]))])
async def import_from_file(file: UploadFile, current_user: User = Depends(get_current_user), import_service: ImportService = Depends(get_import_service)):
    # accept only excel and csv files using media type
    if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # check file size
    if file.size > 1024 * 1024 * 5:  # 5MB
        raise HTTPException(status_code=400, detail="File too large")
    
    return await import_service.process_import_file(file)
    