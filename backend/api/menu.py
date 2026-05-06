import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel, Field

from db.session import get_session
from models.user import User
from models.menu_item import MenuItem
from models.category import Category
from core.security import require_role

menu_router = APIRouter(prefix="/menu", tags=["Menu"])
category_router = APIRouter(prefix="/categories", tags=["Categories"])


# --- Pydantic schemas ---

class MenuItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category_id: int = Field(gt=0)
    price: float = Field(gt=0.0)
    image_url: Optional[str] = Field(default=None, max_length=2000000)
    ingredients: Optional[str] = Field(default=None, max_length=1000)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    dietary_tags: Optional[str] = Field(default=None, max_length=255)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category_id: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, gt=0.0)
    image_url: Optional[str] = Field(default=None, max_length=2000000)
    ingredients: Optional[str] = Field(default=None, max_length=1000)
    is_available: Optional[bool] = None
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    dietary_tags: Optional[str] = Field(default=None, max_length=255)


class MenuItemRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: str
    price: float
    image_url: Optional[str] = None
    ingredients: Optional[str] = None
    is_available: bool
    prep_time_minutes: Optional[int] = None
    dietary_tags: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)


# --- Menu endpoints ---

@menu_router.get("/", response_model=List[MenuItemRead])
async def get_menu(session: Session = Depends(get_session)):
    """Listează toate produsele din meniu cu numele categoriei."""
    statement = select(MenuItem, Category.name).join(Category)
    results = session.exec(statement).all()
    return [
        MenuItemRead(
            id=item.id,
            name=item.name,
            description=item.description,
            category=cat_name,
            price=item.price,
            image_url=item.image_url,
            ingredients=item.ingredients,
            is_available=item.is_available,
            prep_time_minutes=item.prep_time_minutes,
            dietary_tags=item.dietary_tags,
        )
        for item, cat_name in results
    ]


@menu_router.get("/{item_id}", response_model=MenuItemRead)
async def get_menu_item(item_id: int, session: Session = Depends(get_session)):
    """Detalii pentru un singur produs din meniu."""
    db_item = session.get(MenuItem, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produsul nu a fost găsit")
    category = session.get(Category, db_item.category_id)
    return MenuItemRead(
        id=db_item.id,
        name=db_item.name,
        description=db_item.description,
        category=category.name if category else "Unknown",
        price=db_item.price,
        image_url=db_item.image_url,
        ingredients=db_item.ingredients,
        is_available=db_item.is_available,
        prep_time_minutes=db_item.prep_time_minutes,
        dietary_tags=db_item.dietary_tags,
    )


@menu_router.post("/", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    item_in: MenuItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Creează un produs nou în meniu (doar Manager)."""
    category = session.get(Category, item_in.category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria nu există")

    existing = session.exec(select(MenuItem).where(MenuItem.name == item_in.name)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Există deja un produs cu acest nume")

    db_item = MenuItem(**item_in.model_dump())
    session.add(db_item)
    session.commit()
    session.refresh(db_item)

    return MenuItemRead(
        id=db_item.id,
        name=db_item.name,
        description=db_item.description,
        category=category.name,
        price=db_item.price,
        image_url=db_item.image_url,
        ingredients=db_item.ingredients,
        is_available=db_item.is_available,
        prep_time_minutes=db_item.prep_time_minutes,
        dietary_tags=db_item.dietary_tags,
    )


@menu_router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Manager"]))
):
    """
    Process and optimize image: resize to 800x600, compress to WebP format.
    
    - Validates file type and size (max 10MB upload limit)
    - Resizes to 800x600px with aspect ratio preservation
    - Compresses to WebP format (~85% quality)
    - Returns base64 data URL and optimized file size
    """
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format invalid. Acceptăm: JPG, PNG, WebP, GIF"
        )

    contents = await file.read()

    # Magic byte validation (H4 fix) — prevent Content-Type spoofing
    magic_bytes = {
        b'\xff\xd8\xff': "jpeg",
        b'\x89PNG\r\n\x1a\n': "png",
        b'RIFF': "webp",
        b'GIF8': "gif",
    }
    valid = False
    for magic, fmt in magic_bytes.items():
        if contents[:len(magic)] == magic:
            if fmt == "webp" and file.content_type != "image/webp":
                continue  # RIFF is also used by other formats — verify WebP signature deeper
            valid = True
            break
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fișier invalid: semnătura nu corespunde tipului declarat"
        )

    # Validate upload size limit (10MB)
    if len(contents) > 10_000_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imaginea depășește limita de 10 MB"
        )
    
    # Process image
    from core.image_processing import process_image
    try:
        main_image_url, _ = process_image(contents, file.filename or "image")
        # Calculate optimized size from base64 data (rough estimate)
        estimated_size_kb = len(main_image_url) // 1366  # base64 is ~33% larger
        return {
            "image_url": main_image_url,
            "size_kb": max(10, estimated_size_kb),  # Minimum 10KB estimate
            "format": "WebP"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fișier invalid: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eroare la procesarea imaginii: {str(e)}"
        )


@menu_router.put("/{item_id}", response_model=MenuItemRead)
async def update_menu_item(
    item_id: int,
    item_in: MenuItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Actualizează un produs din meniu (doar Manager)."""
    db_item = session.get(MenuItem, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produsul nu a fost găsit")

    update_data = item_in.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        category = session.get(Category, update_data["category_id"])
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria nu există")

    for key, value in update_data.items():
        setattr(db_item, key, value)

    session.add(db_item)
    session.commit()
    session.refresh(db_item)

    category = session.get(Category, db_item.category_id)
    return MenuItemRead(
        id=db_item.id,
        name=db_item.name,
        description=db_item.description,
        category=category.name if category else "Unknown",
        price=db_item.price,
        image_url=db_item.image_url,
        ingredients=db_item.ingredients,
        is_available=db_item.is_available,
        prep_time_minutes=db_item.prep_time_minutes,
        dietary_tags=db_item.dietary_tags,
    )


@menu_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Șterge un produs din meniu (doar Manager)."""
    db_item = session.get(MenuItem, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produsul nu a fost găsit")

    session.delete(db_item)
    session.commit()


# --- Category endpoints ---

@category_router.get("/", response_model=List[CategoryRead])
async def get_categories(session: Session = Depends(get_session)):
    """Listează toate categoriile."""
    categories = session.exec(select(Category)).all()
    return categories


@category_router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Creează o categorie nouă (doar Manager)."""
    existing = session.exec(select(Category).where(Category.name == category_in.name)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Există deja o categorie cu acest nume")

    db_category = Category(**category_in.model_dump())
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@category_router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Actualizează o categorie (doar Manager)."""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria nu a fost găsită")

    if category_in.name and category_in.name != db_category.name:
        existing = session.exec(select(Category).where(Category.name == category_in.name)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Există deja o categorie cu acest nume")

    update_data = category_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)

    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@category_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Șterge o categorie (doar Manager)."""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria nu a fost găsită")

    items_count = len(session.exec(
        select(MenuItem).where(MenuItem.category_id == category_id)
    ).all())

    if items_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nu se poate șterge categoria cu {items_count} produse. Reatribuiți sau ștergeți produsele mai întâi."
        )

    session.delete(db_category)
    session.commit()
