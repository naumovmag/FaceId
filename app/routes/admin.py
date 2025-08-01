from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services.user_service import user_service

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


def require_admin(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    users = user_service.get_all_users(db)
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "title": "Управление пользователями",
            "users": users,
            "page": "admin_users",
        },
    )


@router.post("/users/{user_id}/approve")
async def approve_user(
    request: Request, user_id: int, db: Session = Depends(get_db)
):
    require_admin(request)
    user_service.approve_user(db, user_id)
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request, user_id: int, db: Session = Depends(get_db)
):
    require_admin(request)
    user_service.delete_user(db, user_id)
    return RedirectResponse("/admin/users", status_code=302)
