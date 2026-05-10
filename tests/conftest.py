import pytest
import sys
import os

# Add backend to path for tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'haconcierge', 'rootfs', 'app', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATA_DIR", "/tmp/haconcierge_test")
os.environ.setdefault("SESSION_DIR", "/tmp/haconcierge_test/sessions")
os.environ.setdefault("HA_TOKEN", "test_token")
os.environ.setdefault("HA_URL", "http://localhost:8123")

from database.models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_owner(db):
    from database.models import Owner
    owner = Owner(
        name="Anna",
        phone="491701234567",
        aliases=["Mama", "Mutter", "Anna Müller"],
        notify_on_task=True,
        notify_on_appointment=True,
        notify_on_keyword=True,
        o365_email="anna@test.de",
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@pytest.fixture
def sample_keyword(db, sample_owner):
    from database.models import Keyword
    kw = Keyword(owner_id=sample_owner.id, word="Sport", case_sensitive=False)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw
