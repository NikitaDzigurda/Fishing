from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.service.recommendations.recsys_loader import RecSysService

router = APIRouter(prefix="/recommendations", tags=["RecSys"])

@router.get("/")
async def get_recommendations(
    user_id: int,
    q: str,
    top_n: int = 5,
    use_llm: bool = True
):
    """
    Get recommendations using the loaded RecSys engine.
    """
    recsys = RecSysService.get_instance()
    
    if not recsys:
        raise HTTPException(
            status_code=503, 
            detail="Recommendation engine is warming up or not initialized"
        )
    
    # Call the unmodified 'recommend' method from your class
    try:
        results = recsys.recommend(
            user_id=user_id,
            query_text=q,
            top_n=top_n,
            use_llm=use_llm
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RecSys internal error: {str(e)}")


@router.post("/refresh")
async def refresh_engine(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a reload of the ML engine from the database.
    This runs in the background to avoid blocking the request.
    """
    background_tasks.add_task(RecSysService.load_and_init, db)
    return {"status": "Refresh started in background"}