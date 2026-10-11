from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker


def get_db_session(request: Request) -> Iterator[Session]:
    factory = cast(
        sessionmaker[Session] | None,
        getattr(request.app.state, "session_factory", None),
    )
    if factory is None:
        raise HTTPException(status_code=503)

    with factory() as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_db_session)]
