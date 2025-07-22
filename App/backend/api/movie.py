from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from schema.movie_schema import (
    MovieDetail,
    MovieShortDetail,
    MovieFilter,
    MovieTrailer
)
from service.movie_service import MovieDisplayService
from service.movie_discovery_service import MovieDiscoveryService
from db.config import get_db  # Cập nhật đường dẫn nếu bạn để chỗ khác

router = APIRouter()

# ---- Các route liên quan đến khám phá phim (gợi ý, lọc, trending) ---- #

@router.get("/movies/filter", response_model=List[MovieShortDetail])
async def filter_movies(
    filter_params: MovieFilter = Depends(),
    db: Session = Depends(get_db)
):
    """Filter movies based on various criteria"""
    return await MovieDiscoveryService.filter_movies(filter_params, db)


@router.get("/movies/trending", response_model=List[MovieShortDetail])
async def trending_movies(db: Session = Depends(get_db)):
    """Get trending movies"""
    return await MovieDiscoveryService.get_trending_movies(db)


@router.get("/movies/{movie_id}/recommendations", response_model=List[MovieShortDetail])
async def get_movie_recommendations(movie_id: int, db: Session = Depends(get_db)):
    """Get movie recommendations based on a movie"""
    return await MovieDiscoveryService.get_movie_recommendations(movie_id, db)


# ---- Các route liên quan đến hiển thị chi tiết phim ---- #

@router.get("/movies/{movie_id}", response_model=MovieDetail)
async def get_full_movie(movie_id: int, db: Session = Depends(get_db)):
    """Get full detail of a movie"""
    return await MovieDisplayService.get_movie_detail(movie_id, db)

@router.get("/shortdetail/{movie_id}", response_model=MovieShortDetail)
async def get_movie_short_detail(movie_id: int, db: Session = Depends(get_db)):
    """Get short details of a movie for home page display"""
    return await MovieDisplayService.get_movie_short_detail(movie_id, db)


@router.get("/movies/{movie_id}/trailer", response_model=List[MovieTrailer])
async def get_movie_trailers(movie_id: int, db: Session = Depends(get_db)):
    """Get available trailers for a movie"""
    return await MovieDisplayService.get_movie_trailers(movie_id, db)
