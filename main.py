from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title = "Spottr")

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

