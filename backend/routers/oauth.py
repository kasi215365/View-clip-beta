"""OAuth router — YouTube + Twitch connect, callback, list, disconnect."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from core.auth import get_current_user
from core.models import User
import export_service as svc

router = APIRouter(prefix="/api")


@router.post("/oauth/{provider}/start")
async def oauth_start(provider: str, current_user: User = Depends(get_current_user)):
    """Return the provider auth URL the frontend should redirect to.
    Falls back to `mock=true` if the provider env vars are missing."""
    provider = provider.lower()
    if provider not in {"youtube", "twitch"}:
        raise HTTPException(status_code=400, detail="Unknown provider")
    if not svc.provider_configured(provider):
        return {
            "mock": True,
            "message": f"{provider.title()} OAuth not configured on this deployment. "
                       f"Set {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET.",
        }
    state = await svc.create_state(current_user.id, provider)
    url = svc.build_auth_url(provider, state)
    return {"mock": False, "authorization_url": url, "provider": provider}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    """Providers redirect here. Exchanges code → tokens, persists the connection,
    then redirects the browser back to /streamer-dashboard with a status flag."""
    provider = provider.lower()
    if error:
        return RedirectResponse(url=f"/streamer?oauth={provider}&status=error&msg={error}")
    if not code or not state:
        return RedirectResponse(url=f"/streamer?oauth={provider}&status=error&msg=missing_params")
    user_id = await svc.consume_state(state, provider)
    if not user_id:
        return RedirectResponse(url=f"/streamer?oauth={provider}&status=error&msg=invalid_state")
    try:
        tokens = await svc.exchange_code(provider, code)
        profile = await svc.fetch_provider_profile(provider, tokens["access_token"])
        await svc.save_connection(user_id, provider, tokens, profile)
    except Exception:  # network / HTTP errors
        return RedirectResponse(
            url=f"/streamer?oauth={provider}&status=error&msg=exchange_failed"
        )
    return RedirectResponse(
        url=f"/streamer?oauth={provider}&status=connected"
    )


@router.get("/oauth/connections")
async def oauth_connections(current_user: User = Depends(get_current_user)):
    return await svc.list_connections(current_user.id)


@router.post("/oauth/{provider}/disconnect")
async def oauth_disconnect(provider: str, current_user: User = Depends(get_current_user)):
    provider = provider.lower()
    if provider not in {"youtube", "twitch"}:
        raise HTTPException(status_code=400, detail="Unknown provider")
    ok = await svc.delete_connection(current_user.id, provider)
    return {"disconnected": ok, "provider": provider}
