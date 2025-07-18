from fastapi import FastAPI
from api.movie import router as movie_router
from api.auth import router as auth_router
import uvicorn
app = FastAPI(
    title="Movie API",
    description="API for managing and retrieving movie information",
    version="1.0.0"
)

# Include routers from different modules
app.include_router(
    movie_router,
    prefix="/api/v1",
    tags=["movies"]
)

app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Movie API"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)