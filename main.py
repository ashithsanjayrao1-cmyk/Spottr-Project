from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from database import engine, get_db
import models
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List









load_dotenv()

app = FastAPI(title = "Spottr")

models.Base.metadata.create_all(bind = engine)


client = genai.Client()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")


class ExerciseCreate(BaseModel):
    exercise_name: str
    sets: int
    reps: int
    weight_kg: float

class WorkoutLogCreate(BaseModel):
    workout_name: str
    duration_minutes: int
    exercises: List[ExerciseCreate]


class UserCreate(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register_user(user: UserCreate, db: Session = Depends (get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code = 400, detail = "Email already registered" )

    hashed_password = pwd_context.hash(user.password)

    new_user = models.User(email = user.email, password_hash = hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return{"message": "User created Successfully!","user_id": new_user.id}

class USerLogin(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
  
    existing_user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not existing_user or not pwd_context.verify(form_data.password, existing_user.password_hash):
        raise HTTPException(status_code=404, detail="Invalid Email or Password")

    expire_time = datetime.now(timezone.utc) + timedelta(hours=24)
    token_data = {
        "sub": str(existing_user.id),
        "exp": expire_time
    }

    secret_key = os.getenv("JWT_SECRET")
    token = jwt.encode(token_data, secret_key, algorithm="HS256")

    return {"access_token": token, "token_type": "bearer"}

class ProfileCreate(BaseModel):
    name: str
    gender: str
    age: int
    weight_in_kg: float
    height_in_cm: float
    primary_goal: str
    experience_level: str
    dietary_preferences: str




outh2_scheme = OAuth2PasswordBearer(tokenUrl = "/api/auth/login")
def get_current_user(token: str = Depends(outh2_scheme), db: Session = Depends(get_db)):
    try:
        secret_key = os.getenv("JWT_SECRET")
        payload = jwt.decode(token, secret_key, algorithms = ["HS256"])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code = 401, detail = "Could not validate  credentials")

        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(status_code = 401, detail = "User Not Found")

        return user 

    except jwt.PyJWTError:
        raise HTTPException(status_code = 401, detail = "Invalid or expired token")


@app.post("/api/profile/me")
def create_user_profile(profile: ProfileCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):

    existing_profile = db.query(models.Profile).filter(models.Profile.user_id == current_user.id).first()

    if existing_profile:
        raise HTTPException(status_code = 400, detail = "Profile Already Exists for this user")

    new_profile = models.Profile(**profile.model_dump(), user_id = current_user.id)

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return{"message": "Profile Created Successfully!","profile_id":new_profile.id}
     



#client = genai.Client()

@app.get("/")
async def root():
    return {"message": "Spottr is running. Ready to lift."} 

class UserProfileMock(BaseModel):
    name: str
    gym_branch: str
    primary_goal: str


@app.post("/api/profile/create-mock")
async def create_mock_profile(profile: UserProfileMock):
    return{"status":"Success","data":profile}


class DailyWorkout(BaseModel):
    day : str = Field(description="e.g., Monday,Wednesday,Thursday")
    focus : str = Field(description= "Target Muscle Group")
    exercises : list[str] = Field(description= "List Of Exercises With Sets And Reps")
    notes : str = Field(description="Form Tips Or Posing Practice Reminders")

class DietPlan(BaseModel):
    target_calories: int
    protein_grams: int
    daily_checklist: list[str] = Field(description="Specific Dietary Requirements") 

class AICoachResponse(BaseModel):
    workout_split: list[DailyWorkout]
    nutrition_targets: DietPlan     

class AIRequest(BaseModel):
    primary_goal: str
    experience_level: str
    dietary_preferences: str
    weight_in_kg: float
    height_in_cm: float
    age: int
    gender: str
    phase: str
    days_per_week: int



@app.post("/api/ai/generate-plan")
def generate_ai_plan(
    request: AIRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    system_instruction = """
    You are an elite fitness AI coach for the Spottr app.
    Generate highly personalized workout splits and daily macro plans based on the user's metrics.
    """

    user_prompt = f"""
    Generate a {request.days_per_week}-day workout split and daily macro plan for a user with these stats:
    - Biometrics: {request.age} year old {request.gender}, {request.weight_in_kg}kg, {request.height_in_cm}cm  
    - Current phase: {request.phase} (Calculate calories/macros specifically for this goal)
    - Primary Goal: {request.primary_goal}
    - Experience Level: {request.experience_level}
    - Dietary Requirements: {request.dietary_preferences}
    Ensure the nutrition checklist includes their specific dietary requirements.
    """

    response = client.models.generate_content(
        model = "gemini-3.6-flash",
        contents = user_prompt,
        config = types.GenerateContentConfig(
            system_instruction = system_instruction,
            response_mime_type = "application/json",
            response_schema = AICoachResponse, 
        )
    )

    ai_data = response.parsed

    new_plan = models.FitnessPlan(
        user_id = current_user.id,
        phase = request.phase
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)


    for workout in ai_data.workout_split:
        new_workout = models.WorkoutDay(
            plan_id = new_plan.id,
            day = workout.day,
            focus = workout.focus,
            exercises = ", ".join(workout.exercises),
            notes = workout.notes
        )
        db.add(new_workout)

    new_diet = models.DietTarget(
        plan_id=new_plan.id,
        target_calories=ai_data.nutrition_targets.target_calories,
        protein_grams=ai_data.nutrition_targets.protein_grams,
        daily_checklist=", ".join(ai_data.nutrition_targets.daily_checklist)
    )
    db.add(new_diet)

    db.commit()

    return{
        "message": "Plan generated and saved successfully!", 
        "plan_id": new_plan.id,
        "ai_plan": ai_data

    }


@app.post("/api/workouts/log")
def log_workout(
    request: WorkoutLogCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    new_workout = models.WorkoutLog(
        user_id=current_user.id,
        workout_name=request.workout_name,
        duration_minutes=request.duration_minutes
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)

    for exercise in request.exercises:
        new_exercise = models.ExerciseLog(
            workout_id=new_workout.id,
            exercise_name=exercise.exercise_name,
            sets=exercise.sets,
            reps=exercise.reps,
            weight_kg=exercise.weight_kg
        )
        db.add(new_exercise)

    db.commit()
    
    return {
        "message": "Workout completely logged!", 
        "workout_id": new_workout.id
    }


@app.post("/api/workouts/history")
def get_workout_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workouts=db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id

   ).order_by(models.WorkoutLog.date.desc()).all()

    return workouts


@app.get("/api/fitness-plan.current")

def get_current_plan(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(models.FitnessPlan).filter(
        models.FitnessPlan.user_id == current_user.id
    ).order_by(models.FitnessPlan.id.desc()).first()


    if not plan:
        raise HTTPException(status_code = 404, detail = "No Fitness Plan Found" )

    return plan 



