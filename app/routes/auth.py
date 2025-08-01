from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services.user_service import user_service

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Вход", "page": "login"},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = user_service.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Вход",
                "error": "Неверные данные или пользователь не активирован",
                "page": "login",
            },
            status_code=400,
        )
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["is_admin"] = user.is_admin
    return RedirectResponse("/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "title": "Регистрация", "page": "register"},
    )


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = user_service.get_user_by_username(db, username)
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Регистрация",
                "error": "Пользователь уже существует",
                "page": "register",
            },
            status_code=400,
        )
    is_first = user_service.is_first_user(db)
    user_service.create_user(
        db,
        username,
        password,
        is_admin=is_first,
        is_active=is_first,
    )
    message = (
        "Регистрация успешна. Можете войти." if is_first else "Регистрация прошла. Ожидайте одобрения администратора."
    )
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "Вход",
            "message": message,
            "page": "login",
        },
    )
