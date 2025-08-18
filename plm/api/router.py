
from plm.api.files_upload import router as router_upload
from plm.api.rag_qa import router as router_qa

from fastapi import APIRouter

router = APIRouter()

router.include_router(router_upload, prefix='/upload', tags=["Upload Files to Expand Knowledge"])
router.include_router(router_qa, prefix='/qa', tags=["Generate Answer for User Query with RAG PipeLine"])
