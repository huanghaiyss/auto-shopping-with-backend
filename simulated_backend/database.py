from sqlmodel import SQLModel, Session, create_engine,select
from models import Gift, User

engine = create_engine("sqlite:///data.db")

def init_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(User)).first():
            session.add(User(token="mysecrettoken", stars=50))
        if not session.exec(select(Gift)).first():
            session.add_all([
                Gift(sku="gift_001", name="Exclusive Mug", quantity=10),
                Gift(sku="gift_002", name="Premium Sticker", quantity=5)
            ])
        session.commit()
