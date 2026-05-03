from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class CointegratedPair(Base):
    __tablename__ = 'cointegrated_pairs'
    
    id = Column(Integer, primary_key=True)
    ticker_a = Column(String)
    ticker_b = Column(String)
    beta = Column(Float)
    alpha = Column(Float)
    adf_stat = Column(Float)
    p_value = Column(Float)
    hurst_exponent = Column(Float)
    half_life = Column(Float)
    z_score_threshold = Column(Float, default=2.0)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

def init_db(db_path='sqlite:///pairs_trading.db'):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

if __name__ == "__main__":
    # Just to check if this doesn't explode in my face
    session = init_db()
    print("Database initialized without causing a meltdown.")
