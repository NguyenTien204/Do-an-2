from fastapi import FastAPI
from api.movie import router as movie_router
from api.auth import router as auth_router
from api.search import router as search_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Movie API",
    description="Backend API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers from different modules
app.include_router(
    movie_router,
    prefix="/api/v1",
    tags=["movies"]
)
app.include_router(
    search_router,
    prefix="/api/v1",
    tags=["movies"]
)
app.include_router(
    auth_router,
    prefix="/api/v1",
    tags=["movies"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Movie API"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)
    