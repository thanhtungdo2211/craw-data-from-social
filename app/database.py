from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Lấy thông tin kết nối từ biến môi trường
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "youtube_data")

# Tạo URL kết nối
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Tạo engine
engine = create_engine(DATABASE_URL)

# Tạo Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Khai báo Base
Base = declarative_base()

def get_db():
    """Hàm trả về database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def init_db():
    """Khởi tạo database"""
    from models import Base
    Base.metadata.create_all(bind=engine)