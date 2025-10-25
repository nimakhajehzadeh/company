import asyncio
import json
import logging
from typing import Optional

import aiohttp
from aiocache import cached
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
    SRC_LOG_LEVELS,
)
from open_webui.models.users import UserModel

from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.misc import convert_logit_bias_input_to_json
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])

router = APIRouter()


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url: str, key: Optional[str] = None, user: Optional[UserModel] = None):
    """Generic GET helper to retrieve /models or other resources from external OpenAI-compatible endpoints."""
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                **({"Authorization": f"Bearer {key}"} if key else {}),
                **(
                    {
                        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            }
            async with session.get(url, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL) as response:
                # Try to parse JSON; return None on parse/connection failure
                try:
                    return await response.json()
                except Exception:
                    text = await response.text()
                    log.debug(f"send_get_request non-json response for {url}: {text}")
                    return None
    except Exception as e:
        log.error(f"Connection error for {url}: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def openai_reasoning_model_handler(payload: dict) -> dict:
    """
    Handle reasoning-model-specific parameters.
    - Convert max_tokens -> max_completion_tokens for reasoning models.
    - Convert initial system role for legacy models.
    """
    if "max_tokens" in payload:
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    if "messages" in payload and payload["messages"]:
        if payload["messages"][0].get("role") == "system":
            model_lower = payload.get("model", "").lower()
            # Legacy reasoning models expect "user" instead of "system"
            if model_lower.startswith(("o1-mini", "o1-preview")):
                payload["messages"][0]["role"] = "user"
            else:
                payload["messages"][0]["role"] = "developer"

    return payload


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    """
    Query all configured OPENAI_API_BASE_URLS for /models and return raw responses list.
    Returns list aligned with OPENAI_API_BASE_URLS (some entries may be None).
    """
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Normalize keys length to url length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        if num_keys > num_urls:
            request.app.state.config.OPENAI_API_KEYS = request.app.state.config.OPENAI_API_KEYS[:num_urls]
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        # Determine api_config for this url (legacy support included)
        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),
        )

        enable = api_config.get("enable", True)
        model_ids = api_config.get("model_ids", [])

        if not enable:
            # Keep placeholder to preserve ordering
            request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))
            continue

        if model_ids:
            # If explicit list provided, create a synthetic models list to avoid querying external endpoint
            model_list = {
                "object": "list",
                "data": [
                    {
                        "id": model_id,
                        "name": model_id,
                        "owned_by": "openai",
                        "openai": {"id": model_id},
                        "urlIdx": idx,
                    }
                    for model_id in model_ids
                ],
            }
            request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, model_list)))
        else:
            request_tasks.append(
                send_get_request(f"{url}/models", request.app.state.config.OPENAI_API_KEYS[idx], user=user)
            )

    responses = await asyncio.gather(*request_tasks)
    return responses


async def get_filtered_models(models: dict, user: UserModel):
    """Filter models using model access control logic for non-admin users."""
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(user.id, type="read", access_control=model_info.access_control):
                filtered_models.append(model)
    return filtered_models


@cached(ttl=MODELS_CACHE_TTL)
async def get_all_models(request: Request, user: UserModel) -> dict:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and isinstance(response, dict) and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def merge_models_lists(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        merged_list = []

        for idx, models_chunk in enumerate(model_lists):
            if models_chunk is not None and "error" not in (models_chunk or {}):
                for model in models_chunk:
                    # Remove name if None
                    if model.get("name") is None:
                        model.pop("name", None)

                    merged_list.append(
                        {
                            **model,
                            "name": model.get("name", model.get("id", "")),
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }
                    )

        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    # Cache models in application state for later lookup
    request.app.state.OPENAI_MODELS = {model["id"]: model for model in models["data"]}
    return models


##########################################
#
# Routes: config, models, verify, chat, embeddings, proxy
#
##########################################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Normalize lengths between keys and urls
    if len(request.app.state.config.OPENAI_API_KEYS) != len(request.app.state.config.OPENAI_API_BASE_URLS):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(request.app.state.config.OPENAI_API_BASE_URLS):
            request.app.state.config.OPENAI_API_KEYS = request.app.state.config.OPENAI_API_KEYS[
                : len(request.app.state.config.OPENAI_API_BASE_URLS)
            ]
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS) - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Keep only API configs that correspond to existing URLs (legacy keys are numeric indexes)
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {"data": []}

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),
        )

        # If api_config includes an explicit list of model_ids, return them; otherwise query the /models endpoint
        if api_config.get("model_ids"):
            models = {"data": api_config.get("model_ids", []) or [], "object": "list"}
        else:
            r = None
            async with aiohttp.ClientSession(
                trust_env=True,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
            ) as session:
                try:
                    headers = {
                        "Content-Type": "application/json",
                        **(
                            {
                                "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                                "X-OpenWebUI-User-Id": user.id,
                                "X-OpenWebUI-User-Email": user.email,
                                "X-OpenWebUI-User-Role": user.role,
                            }
                            if ENABLE_FORWARD_USER_INFO_HEADERS
                            else {}
                        ),
                        "Authorization": f"Bearer {key}",
                    }

                    async with session.get(f"{url}/models", headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
                        if r.status != 200:
                            try:
                                res = await r.json()
                            except Exception:
                                res = await r.text()
                            error_detail = f"HTTP Error: {r.status} - {res}"
                            raise Exception(error_detail)

                        response_data = await r.json()

                        # Filter out certain OpenAI internal models (legacy filtering)
                        if "api.openai.com" in url:
                            response_data["data"] = [
                                model
                                for model in response_data.get("data", [])
                                if not any(
                                    name in model.get("id", "")
                                    for name in ["babbage", "dall-e", "davinci", "embedding", "tts", "whisper"]
                                )
                            ]

                        models = response_data
                except aiohttp.ClientError as e:
                    log.exception(f"Client error fetching models from {url}: {str(e)}")
                    raise HTTPException(status_code=500, detail="Open WebUI: Server Connection Error")
                except Exception as e:
                    log.exception(f"Unexpected error fetching models from {url}: {e}")
                    raise HTTPException(status_code=500, detail=str(e))

    # Apply access control filtering for regular users unless bypass is enabled
    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str
    config: Optional[dict] = None


@router.post("/verify")
async def verify_connection(form_data: ConnectionVerificationForm, user=Depends(get_admin_user)):
    """
    Verify that given URL/key is reachable and returns the /models list.
    Azure-specific handling has been removed; this always uses Bearer Authorization and calls {url}/models.
    """
    url = form_data.url
    key = form_data.key

    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    ) as session:
        try:
            headers = {
                "Content-Type": "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
                "Authorization": f"Bearer {key}",
            }

            async with session.get(f"{url}/models", headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
                try:
                    response_data = await r.json()
                except Exception:
                    response_data = await r.text()

                if r.status != 200:
                    if isinstance(response_data, (dict, list)):
                        return JSONResponse(status_code=r.status, content=response_data)
                    else:
                        return PlainTextResponse(status_code=r.status, content=response_data)

                return response_data

        except aiohttp.ClientError as e:
            log.exception(f"Client error verifying connection to {url}: {str(e)}")
            raise HTTPException(status_code=500, detail="Open WebUI: Server Connection Error")
        except Exception as e:
            log.exception(f"Unexpected error verifying connection to {url}: {e}")
            raise HTTPException(status_code=500, detail="Open WebUI: Server Connection Error")


def is_openai_reasoning_model(model: str) -> bool:
    return model.lower().startswith(("o1", "o3", "o4", "gpt-5"))


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    # Allow bypass via global config
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Apply model-specific parameters and system prompt if model is a stored model
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()
        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_openai(params, payload)
            payload = apply_system_prompt_to_body(system, payload, metadata, user)

        # Check model access for non-bypass regular users
        if not bypass_filter and user.role == "user":
            if not (user.id == model_info.user_id or has_access(user.id, type="read", access_control=model_info.access_control)):
                raise HTTPException(status_code=403, detail="Model not found")
    else:
        # If model is not found locally, non-admins are blocked
        if not bypass_filter and user.role != "admin":
            raise HTTPException(status_code=403, detail="Model not found")

    # Ensure global model cache is populated
    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(status_code=404, detail="Model not found")

    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(request.app.state.config.OPENAI_API_BASE_URLS[idx], {}),
    )
    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # If model is a pipeline, attach user metadata
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Reasoning model adjustments
    if is_openai_reasoning_model(payload.get("model", "")):
        payload = openai_reasoning_model_handler(payload)
    else:
        # Backwards compatibility: handle max_completion_tokens conversion
        if "max_completion_tokens" in payload and "max_tokens" not in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    # Ensure logit_bias is a JSON object
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(convert_logit_bias_input_to_json(payload["logit_bias"]))

    headers = {
        "Content-Type": "application/json",
        **(
            {
                "HTTP-Referer": "https://openwebui.com/",
                "X-Title": "Open WebUI",
            }
            if "openrouter.ai" in url
            else {}
        ),
        **(
            {
                "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                "X-OpenWebUI-User-Id": user.id,
                "X-OpenWebUI-User-Email": user.email,
                "X-OpenWebUI-User-Role": user.role,
                **({"X-OpenWebUI-Chat-Id": metadata.get("chat_id")} if metadata and metadata.get("chat_id") else {}),
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS
            else {}
        ),
    }

    # Always use standard Bearer Authorization /chat/completions endpoint
    request_url = f"{url}/chat/completions"
    headers["Authorization"] = f"Bearer {key}"

    payload_body = json.dumps(payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(method="POST", url=request_url, data=payload_body, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL)

        # Streamed SSE handling
        content_type = r.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(cleanup_response, response=r, session=session),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(f"Non-JSON chat completion response: {e}")
                response = await r.text()

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            return response
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=r.status if r else 500, detail="Open WebUI: Server Connection Error")
    finally:
        if not streaming:
            await cleanup_response(r, session)


@router.post("/embeddings")
async def embeddings(request: Request, form_data: dict, user=Depends(get_verified_user)):
    """
    Calls the embeddings endpoint for OpenAI-compatible providers.
    """
    # Default index
    idx = 0
    body = json.dumps(form_data)

    # Resolve model -> backend idx if present
    await get_all_models(request, user=user)
    model_id = form_data.get("model")
    models = request.app.state.OPENAI_MODELS or {}
    if model_id in models:
        idx = models[model_id]["urlIdx"]

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    r = None
    session = None
    streaming = False
    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method="POST",
            url=f"{url}/embeddings",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user
                    else {}
                ),
            },
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        content_type = r.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(cleanup_response, response=r, session=session),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(status_code=r.status, content=response_data)

            return response_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=r.status if r else 500, detail="Open WebUI: Server Connection Error")
    finally:
        if not streaming:
            await cleanup_response(r, session)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Generic proxy to configured primary OpenAI-compatible endpoint (deprecated route kept for backward compatibility).
    Azure handling removed — proxies requests to {base_url}/{path} using Bearer Authorization.
    """
    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx), request.app.state.config.OPENAI_API_CONFIGS.get(url, {})
    )

    r = None
    session = None
    streaming = False

    try:
        headers = {
            "Content-Type": "application/json",
            **(
                {
                    "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                    "X-OpenWebUI-User-Id": user.id,
                    "X-OpenWebUI-User-Email": user.email,
                    "X-OpenWebUI-User-Role": user.role,
                }
                if ENABLE_FORWARD_USER_INFO_HEADERS
                else {}
            ),
            "Authorization": f"Bearer {key}",
        }

        request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(method=request.method, url=request_url, data=body, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL)

        content_type = r.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(cleanup_response, response=r, session=session),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(status_code=r.status, content=response_data)

            return response_data

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=r.status if r else 500, detail="Open WebUI: Server Connection Error")
    finally:
        if not streaming:
            await cleanup_response(r, session)
