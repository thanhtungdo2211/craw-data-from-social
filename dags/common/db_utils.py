from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class YouTubeVideo(Base):
    __tablename__ = 'youtube_videos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(255), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    transcript = Column(Text, nullable=True)

