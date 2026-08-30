from sqlalchemy import Column,Integer,String,Float,ForeignKey,JSON,Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index = True)
    email = Column(String(255),unique = True, index = True) 
    password_hash = Column(String(255))

    profile = relationship("Profile", back_populates = "owner", uselist = False)
    workout_plans = relationship("WorkoutPlan", back_populates= "owner")

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key = True, index= True)
    user_id = Column(Integer, ForeignKey("users.id")) 

    name = Column(String(100))
    gender = Column(String(50))
    age = Column(Integer)
    weight_in_kg = Column(Float)
    height_in_cm = Column(Float)

    primary_goal = Column(String(265))
    experience_level = Column(String(100))
    dietary_preferences = Column(String(500))

    owner = relationship("User", back_populates = "profile")

class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("users.id"))
    phase = Column(String(200))

    #saving entire gemini response
    ai_response = Column(JSON)

    owner = relationship("User", back_populates = "workout_plans")

class FitnessPlan(Base):
    __tablename__ = "fitness_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    phase = Column(String(100))
    
    workouts = relationship("WorkoutDay", back_populates="plan")
    diet = relationship("DietTarget", uselist=False, back_populates="plan")

class WorkoutDay(Base):
    __tablename__ = "workout_days"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fitness_plans.id"))
    day = Column(String(50))
    focus = Column(String(100))
    exercises = Column(Text) 
    notes = Column(Text)
    
    plan = relationship("FitnessPlan", back_populates="workouts")

class DietTarget(Base):
    __tablename__ = "diet_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fitness_plans.id"))
    target_calories = Column(Integer)
    protein_grams = Column(Integer)
    daily_checklist = Column(Text) 
    
    plan = relationship("FitnessPlan", back_populates="diet")