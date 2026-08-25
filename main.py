from fastapi import FastAPI
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv


load_dotenv()

app = FastAPI(title = "Spottr")


client = genai.Client()

@app.get("/")
async def root():
    return {"message": "Spottr is running. Ready to lift."} 

class UserProfile(BaseModel):
    name: str
    gym_branch: str
    primary_goal: str


@app.post("/api/profile/create")
async def create_profile(profile: UserProfile):
    return{"status":"Success","data":profile}


class DailyWorkout(BaseModel):
    day : str = Field(description="e.g., Monday,Wednesday,Thursday")
    focus : str = Field(description= "Target Muscle Group")
    exercises : list[str] = Field(description= "List Of Exercises With Sets And Reps")
    notes : str = Field(description="Form Tips Or Posing Practice Reminders")

class DietPlan(BaseModel):
    target_calories: int
    protien_grams: int
    daily_checklist: list[str] = Field(description="Specific Dietary Requirements") 

class AICoachResponse(BaseModel):
    workout_split: list[DailyWorkout]
    nutrition_targets: DietPlan     

class AIRequest(BaseModel):
    primary_goal: str
    experience_level: str
    dietary_preferences: str
    weight_in_kg: float
    heigh_in_cm: float
    age: int
    gender: str
    phase: str
    days_per_week: int



@app.post("/api/ai/generate-plan")
async def generate_ai_plan(request: AIRequest):
    system_instruction = """"
    You are an elite fitness AI coach for the Spottr app.
    Generate highly personalized workout splits and daily macro plans based on the user's metrics.
    """

    user_prompt = f""""
    Generate a {request.days_per_week}-day workout split and daily macro plan for a user with these stats:
    -Biometrics: {request.age} year old {request.gender},{request.weight_in_kg}kg,{request.heigh_in_cm} cm  
    -Current phase: {request.phase}(Calculate calories/macros specifically for this goal)
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

    return{"status":"success","ai_plan": response.parsed}