import os
from threading import BoundedSemaphore

from starlette.responses import JSONResponse


class BodyTooLarge(Exception):
    pass


class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.upload_slot = BoundedSemaphore(1)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def reject(detail, status):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

        method = scope["method"]
        path = scope["path"]
        session = scope.get("session", {})
        if method == "POST" and path not in {"/login", "/login/alumno"} and not (
            session.get("authenticated") is True or session.get("student_id")
        ):
            await reject("Inicia sesión antes de enviar archivos o solicitudes.", 403)
            return

        limit = 128 * 1024
        if path == "/mis-tareas/ingles/pronunciacion/evaluar":
            limit = 700 * 1024
        elif path in {"/documents", "/mis-tareas/clase/material"}:
            limit = 66 * 1024 * 1024
        elif path in {"/tutor/conversacion", "/mis-tareas/clase/transcribir"}:
            limit = 9 * 1024 * 1024
        elif path.endswith(("/review", "/revisar")):
            limit = 2 * 1024 * 1024
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    await reject("Longitud de solicitud no válida.", 400)
                    return
                if declared < 0 or declared > limit:
                    await reject("La solicitud supera el tamaño permitido.", 413)
                    return

        consumed = 0
        oversized = False
        error_sent = False

        async def bounded_receive():
            nonlocal consumed, oversized
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > limit:
                    oversized = True
                    raise BodyTooLarge()
            return message

        async def secured_send(message):
            nonlocal error_sent
            if oversized:
                if not error_sent:
                    error_sent = True
                    await reject("La solicitud supera el tamaño permitido.", 413)
                return
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"same-origin"),
                    (b"content-security-policy", b"frame-ancestors 'none'; base-uri 'self'; object-src 'none'"),
                ])
                if os.getenv("APP_COOKIE_SECURE", "false").lower() == "true":
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                message = {**message, "headers": headers}
            await send(message)

        uploading = method == "POST" and path in {"/documents", "/mis-tareas/clase/material"}
        if uploading and not self.upload_slot.acquire(blocking=False):
            await reject("Se está procesando otra subida. Espera un momento y vuelve a intentarlo.", 429)
            return
        try:
            await self.app(scope, bounded_receive, secured_send)
        except BodyTooLarge:
            if not error_sent:
                await reject("La solicitud supera el tamaño permitido.", 413)
        finally:
            if uploading:
                self.upload_slot.release()
