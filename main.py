import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List

# Define strictly validated input payload
class PredictionInput(BaseModel):
    features: List[float] = Field(
        ..., 
        examples=[[5.1, 3.5, 1.4, 0.2]], 
        description="List of 4 numeric features: sepal length, sepal width, petal length, petal width"
    )

class PredictionResponse(BaseModel):
    class_id: int
    class_name: str
    probabilities: List[float]

app = FastAPI(title="Deployable ML Model API", version="1.0.0")

# Load model artifact at module initialization
artifact = joblib.load("model.joblib")
model = artifact["model"]
target_names = artifact["target_names"]

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": True}

@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionInput):
    if len(payload.features) != 4:
        raise HTTPException(
            status_code=400, 
            detail="Exactly 4 numeric features are required."
        )

    # Perform inference
    features_array = [payload.features]
    prediction = int(model.predict(features_array)[0])
    probabilities = model.predict_proba(features_array)[0].tolist()

    return {
        "class_id": prediction,
        "class_name": target_names[prediction],
        "probabilities": [round(p, 4) for p in probabilities]
    }
