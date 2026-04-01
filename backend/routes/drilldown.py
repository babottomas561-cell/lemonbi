from fastapi import APIRouter, Request

from backend.services.drilldown import get_drilldown_payload

router = APIRouter()


@router.get("/{kind}/{panel}/{item}")
def get_drilldown(kind: str, panel: str, item: str, request: Request):
    filters_key = tuple(sorted((str(key), str(value)) for key, value in dict(request.query_params).items()))
    return get_drilldown_payload(kind=kind, panel=panel, item=item, filters_key=filters_key)
