from sqlalchemy import text
from app.db.session import Base
# Import all models to ensure they are registered with the Base metadata before create_all
from app.models.models import Document, DocumentMetadata, Chunk, ChatSession, ChatMessage, UserLimit

def init_db(engine):
    with engine.connect() as conn:
        # Create pgvector extension if it doesn't exist
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    # Reset schema for migration
    print("Dropping old database tables...")
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    print("Recreating database tables with new schema...")
    Base.metadata.create_all(bind=engine)
