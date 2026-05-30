"""ORM models. Importing this package registers every table on ``Base.metadata``
(used by Alembic autogenerate and by ``Base.metadata.create_all`` in tests)."""

from app.models.chunk import Chunk
from app.models.constants import DocumentStatus, ExtractionMethod
from app.models.document import Document
from app.models.document_image import DocumentImage
from app.models.query_log import QueryLog
from app.models.user import User

__all__ = [
    "Chunk",
    "Document",
    "DocumentImage",
    "DocumentStatus",
    "ExtractionMethod",
    "QueryLog",
    "User",
]
