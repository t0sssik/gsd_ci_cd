from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid
import random
from enum import Enum

app = FastAPI(title="GSD Assessment API", version="1.0.0")

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = []
images_db = []
models_db = []
assessments_db = []
quality_metrics_db = []

# User Models
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole = UserRole.USER

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    id: int
    registration_date: datetime
    api_key: str

# Image Models  
class ImageStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ImageBase(BaseModel):
    filename: str
    file_size: int
    width: int = 1920
    height: int = 1080
    format: str = "jpg"

class ImageCreate(ImageBase):
    user_id: int

class ImageUpdate(BaseModel):
    filename: Optional[str] = None
    status: Optional[ImageStatus] = None

class ImageResponse(ImageBase):
    id: int
    user_id: int
    upload_date: datetime
    status: ImageStatus

# Model Models
class ModelBase(BaseModel):
    model_name: str
    version: str
    architecture: str = "ResNet50"
    accuracy: float = 0.95
    is_active: bool = True

class ModelCreate(ModelBase):
    pass

class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    is_active: Optional[bool] = None

class ModelResponse(ModelBase):
    id: int
    training_date: datetime

# Assessment Models
class AssessmentBase(BaseModel):
    image_id: int
    model_id: int
    gsd_value: float
    confidence_score: float = 0.9
    processing_time: float = 1.5

class AssessmentCreate(AssessmentBase):
    pass

class AssessmentUpdate(BaseModel):
    gsd_value: Optional[float] = None
    confidence_score: Optional[float] = None

class AssessmentResponse(AssessmentBase):
    id: int
    assessment_date: datetime

class QualityMetricsBase(BaseModel):
    sharpness_score: float = 0.8
    noise_level: float = 0.1
    contrast_ratio: float = 2.5
    blur_detected: bool = False
    quality_grade: str = "good"

# ========== USERS ==========

# 1. GET /api/v1/users - список пользователей
@app.get("/api/v1/users", response_model=List[UserResponse])
def get_users():
    """Получить список всех пользователей"""
    return users_db

# 2. GET /api/v1/users/{id} - информация о пользователе
@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """Получить информацию о конкретном пользователе"""
    for user in users_db:
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")

# 3. POST /api/v1/users - создание пользователя
@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate):
    """Создать нового пользователя"""
    # Проверка уникальности email и username
    for existing_user in users_db:
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if existing_user["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    new_user = {
        "id": len(users_db) + 1,
        **user.dict(),
        "registration_date": datetime.now(),
        "api_key": str(uuid.uuid4())[:20]  # Генерация API ключа
    }
    users_db.append(new_user)
    return new_user

# 4. PUT /api/v1/users/{id} - обновление пользователя
@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate):
    """Обновить информацию о пользователе"""
    for user in users_db:
        if user["id"] == user_id:
            update_data = user_update.dict(exclude_unset=True)
            user.update(update_data)
            return user
    raise HTTPException(status_code=404, detail="User not found")

# 5. DELETE /api/v1/users/{id} - удаление пользователя
@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: int):
    """Удалить пользователя"""
    for i, user in enumerate(users_db):
        if user["id"] == user_id:
            # Удаляем связанные изображения пользователя
            global images_db, assessments_db
            images_db = [img for img in images_db if img["user_id"] != user_id]
            # Удаляем оценки для удаленных изображений
            image_ids = [img["id"] for img in images_db]
            assessments_db = [a for a in assessments_db if a["image_id"] in image_ids]
            
            deleted_user = users_db.pop(i)
            return {"message": f"User '{deleted_user['username']}' deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")

# ========== IMAGES ==========

# 6. GET /api/v1/images - список изображений
@app.get("/api/v1/images", response_model=List[ImageResponse])
def get_images():
    """Получить список всех изображений"""
    return images_db

# 7. GET /api/v1/images/{id} - информация об изображении
@app.get("/api/v1/images/{image_id}", response_model=ImageResponse)
def get_image(image_id: int):
    """Получить информацию о конкретном изображении"""
    for image in images_db:
        if image["id"] == image_id:
            return image
    raise HTTPException(status_code=404, detail="Image not found")

# 8. POST /api/v1/images - загрузка изображения
@app.post("/api/v1/images", response_model=ImageResponse, status_code=201)
def create_image(image: ImageCreate):
    """Загрузить новое изображение"""
    # Проверяем существование пользователя
    if not any(u["id"] == image.user_id for u in users_db):
        raise HTTPException(status_code=404, detail="User not found")
    
    new_image = {
        "id": len(images_db) + 1,
        **image.dict(),
        "upload_date": datetime.now(),
        "status": ImageStatus.UPLOADED
    }
    images_db.append(new_image)
    return new_image

# 9. PUT /api/v1/images/{id} - обновление метаданных
@app.put("/api/v1/images/{image_id}", response_model=ImageResponse)
def update_image(image_id: int, image_update: ImageUpdate):
    """Обновить метаданные изображения"""
    for image in images_db:
        if image["id"] == image_id:
            update_data = image_update.dict(exclude_unset=True)
            image.update(update_data)
            return image
    raise HTTPException(status_code=404, detail="Image not found")

# 10. DELETE /api/v1/images/{id} - удаление изображения
@app.delete("/api/v1/images/{image_id}")
def delete_image(image_id: int):
    """Удалить изображение"""
    for i, image in enumerate(images_db):
        if image["id"] == image_id:
            # Удаляем связанные оценки
            global assessments_db
            assessments_db = [a for a in assessments_db if a["image_id"] != image_id]
            
            deleted_image = images_db.pop(i)
            return {"message": f"Image '{deleted_image['filename']}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Image not found")

# ========== NEURAL NETWORK MODELS ==========

# 11. GET /api/v1/models - список моделей
@app.get("/api/v1/models", response_model=List[ModelResponse])
def get_models():
    """Получить список всех нейросетевых моделей"""
    return models_db

# 12. GET /api/v1/models/{id} - информация о модели
@app.get("/api/v1/models/{model_id}", response_model=ModelResponse)
def get_model(model_id: int):
    """Получить информацию о конкретной модели"""
    for model in models_db:
        if model["id"] == model_id:
            return model
    raise HTTPException(status_code=404, detail="Model not found")

# 13. POST /api/v1/models - регистрация модели
@app.post("/api/v1/models", response_model=ModelResponse, status_code=201)
def create_model(model: ModelCreate):
    """Зарегистрировать новую модель"""
    new_model = {
        "id": len(models_db) + 1,
        **model.dict(),
        "training_date": datetime.now()
    }
    models_db.append(new_model)
    return new_model

# 14. PUT /api/v1/models/{id} - обновление модели
@app.put("/api/v1/models/{model_id}", response_model=ModelResponse)
def update_model(model_id: int, model_update: ModelUpdate):
    """Обновить информацию о модели"""
    for model in models_db:
        if model["id"] == model_id:
            update_data = model_update.dict(exclude_unset=True)
            model.update(update_data)
            return model
    raise HTTPException(status_code=404, detail="Model not found")

# 15. DELETE /api/v1/models/{id} - удаление модели
@app.delete("/api/v1/models/{model_id}")
def delete_model(model_id: int):
    """Удалить модель"""
    for i, model in enumerate(models_db):
        if model["id"] == model_id:
            deleted_model = models_db.pop(i)
            return {"message": f"Model '{deleted_model['model_name']}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Model not found")

# ========== GSD ASSESSMENTS ==========

# 16. GET /api/v1/assessments - список оценок
@app.get("/api/v1/assessments", response_model=List[AssessmentResponse])
def get_assessments():
    """Получить список всех оценок GSD"""
    return assessments_db

# 17. GET /api/v1/assessments/{id} - результаты оценки
@app.get("/api/v1/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(assessment_id: int):
    """Получить результаты конкретной оценки"""
    for assessment in assessments_db:
        if assessment["id"] == assessment_id:
            return assessment
    raise HTTPException(status_code=404, detail="Assessment not found")

# 18. POST /api/v1/assessments - создание новой оценки
@app.post("/api/v1/assessments", response_model=AssessmentResponse, status_code=201)
def create_assessment(assessment: AssessmentCreate):
    """Создать новую оценку GSD (с генерацией случайного значения)"""
    # Проверяем существование изображения и модели (оставим эту логику)
    if not any(i["id"] == assessment.image_id for i in images_db):
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not any(m["id"] == assessment.model_id for m in models_db):
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Генерируем случайное значение GSD
    random_gsd = round(random.uniform(0, 9), 2)

    new_assessment = {
        "id": len(assessments_db) + 1,
        "image_id": assessment.image_id,
        "model_id": assessment.model_id,
        "gsd_value": random_gsd, # Используем случайное значение
        "confidence_score": round(random.uniform(0.5, 1.0), 2),
        "processing_time": round(random.uniform(0.1, 2.0), 2),
        "assessment_date": datetime.now()
    }
    assessments_db.append(new_assessment)

    quality_metrics = {
        "id": len(quality_metrics_db) + 1,
        "assessment_id": new_assessment["id"],
        "sharpness_score": 0.8,
        "noise_level": 0.1,
        "contrast_ratio": 2.5,
        "blur_detected": False,
        "quality_grade": "good"
    }
    quality_metrics_db.append(quality_metrics)
    
    return new_assessment

# 19. PUT /api/v1/assessments/{id} - обновление оценки
@app.put("/api/v1/assessments/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(assessment_id: int, assessment_update: AssessmentUpdate):
    """Обновить оценку GSD"""
    for assessment in assessments_db:
        if assessment["id"] == assessment_id:
            update_data = assessment_update.dict(exclude_unset=True)
            assessment.update(update_data)
            return assessment
    raise HTTPException(status_code=404, detail="Assessment not found")

# 20. DELETE /api/v1/assessments/{id} - удаление оценки
@app.delete("/api/v1/assessments/{assessment_id}")
def delete_assessment(assessment_id: int):
    """Удалить оценку GSD"""
    for i, assessment in enumerate(assessments_db):
        if assessment["id"] == assessment_id:
            # Удаляем связанные метрики качества
            global quality_metrics_db
            quality_metrics_db = [qm for qm in quality_metrics_db if qm["assessment_id"] != assessment_id]
            
            deleted_assessment = assessments_db.pop(i)
            return {"message": f"Assessment for image {deleted_assessment['image_id']} deleted successfully"}
    raise HTTPException(status_code=404, detail="Assessment not found")

# 21. GET /api/v1/images/{id}/assessments - оценки для конкретного изображения
@app.get("/api/v1/images/{image_id}/assessments", response_model=List[AssessmentResponse])
def get_image_assessments(image_id: int):
    """Получить все оценки для конкретного изображения"""
    # Проверяем существование изображения
    if not any(i["id"] == image_id for i in images_db):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return [a for a in assessments_db if a["image_id"] == image_id]

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========

@app.get("/")
def root():
    """Корневой endpoint с информацией об API"""
    return {
        "message": "GSD Assessment API",
        "version": "1.0.0",
        "total_endpoints": 21,
        "documentation": "/docs",
        "endpoints_by_category": {
            "users": ["GET /api/v1/users", "GET /api/v1/users/{id}", "POST /api/v1/users", "PUT /api/v1/users/{id}", "DELETE /api/v1/users/{id}"],
            "images": ["GET /api/v1/images", "GET /api/v1/images/{id}", "POST /api/v1/images", "PUT /api/v1/images/{id}", "DELETE /api/v1/images/{id}"],
            "models": ["GET /api/v1/models", "GET /api/v1/models/{id}", "POST /api/v1/models", "PUT /api/v1/models/{id}", "DELETE /api/v1/models/{id}"],
            "assessments": ["GET /api/v1/assessments", "GET /api/v1/assessments/{id}", "POST /api/v1/assessments", "PUT /api/v1/assessments/{id}", "DELETE /api/v1/assessments/{id}", "GET /api/v1/images/{id}/assessments"]
        }
    }

@app.post("/api/v1/reset")
def reset_data():
    """Сбросить все данные (только для тестирования)"""
    global users_db, images_db, models_db, assessments_db, quality_metrics_db
    users_db.clear()
    images_db.clear()
    models_db.clear()
    assessments_db.clear()
    quality_metrics_db.clear()
    return {"message": "All data reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)