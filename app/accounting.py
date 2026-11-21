"""Local consumption ledger. Provider balances are deliberately not inferred."""
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


context = ContextVar("aula_usage_context", default=(None, "unknown"))
started_calls = ContextVar("aula_usage_started_calls", default=0)
blocked_before_call = ContextVar("aula_usage_blocked_before_call", default=False)
_factory = None
_legacy = None


class Base(DeclarativeBase):
    pass


class Consumption(Base):
    __tablename__ = "ai_consumption_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    profile_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    actor: Mapped[str] = mapped_column(String(12), default="unknown")
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30), index=True)
    task: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(15), default="pending")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0)
    text_characters: Mapped[int] = mapped_column(Integer, default=0)
    azure_units: Mapped[int] = mapped_column(Integer, default=0)
    audio_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    legacy_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class Budget(Base):
    __tablename__ = "ai_consumption_budgets"
    scope_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0 = family; otherwise profile ID
    monthly_tokens: Mapped[int] = mapped_column(Integer, default=0)
    block: Mapped[bool] = mapped_column(Boolean, default=False)


class BudgetExceeded(Exception):
    pass


def configure(engine, legacy):
    global _factory, _legacy
    _factory = sessionmaker(bind=engine, expire_on_commit=False)
    _legacy = legacy


def month_start():
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def number(value):
    return value if type(value) is int and value >= 0 else None


def token_counts(usage):
    usage = usage if isinstance(usage, dict) else {}
    incoming = number(usage.get("input_tokens", usage.get("prompt_tokens")))
    outgoing = number(usage.get("output_tokens", usage.get("completion_tokens")))
    details = usage.get("input_token_details") or usage.get("prompt_tokens_details") or {}
    cached = number(details.get("cached_tokens")) if isinstance(details, dict) else None
    return incoming, outgoing, cached


def _unassigned_legacy(db, since):
    linked = select(Consumption.legacy_id).where(Consumption.legacy_id.is_not(None))
    return db.scalars(select(_legacy).where(_legacy.created_at >= since, _legacy.id.not_in(linked))).all()


def spent(db, profile_id=None):
    query = select(Consumption).where(Consumption.kind == "text", Consumption.created_at >= month_start())
    if profile_id is not None:
        query = query.where(Consumption.profile_id == profile_id)
    total = sum((e.input_tokens or 0) + (e.output_tokens or 0) + e.reserved_tokens for e in db.scalars(query))
    if profile_id is None:
        total += sum(e.input_tokens + e.output_tokens for e in _unassigned_legacy(db, month_start()))
    return total


def _lock_budget(db, scope_id):
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    db.execute(insert(Budget).values(scope_id=scope_id, monthly_tokens=0, block=False)
               .on_conflict_do_nothing(index_elements=["scope_id"]))
    return db.get(Budget, scope_id, with_for_update=True)


def begin(kind, provider, model, task, *, reserved_tokens=0, text_characters=0, azure_units=0):
    profile_id, actor = context.get()
    with _factory() as db:
        if kind == "text":
            # Lock the family first, then the pupil: serialize reservations across workers.
            policies = [_lock_budget(db, 0)]
            if profile_id is not None:
                policies.append(_lock_budget(db, profile_id))
            for policy in policies:
                if policy.block and policy.monthly_tokens and spent(db, policy.scope_id or None) + reserved_tokens > policy.monthly_tokens:
                    blocked_before_call.set(started_calls.get() == 0)
                    raise BudgetExceeded("Se ha alcanzado el presupuesto mensual de tokens de texto o no queda margen para reservar otra respuesta. Habla con el adulto.")
        event = Consumption(profile_id=profile_id, actor=actor, provider=provider, model=model, kind=kind, task=task,
                            reserved_tokens=reserved_tokens, text_characters=text_characters, azure_units=azure_units)
        db.add(event)
        db.commit()
        started_calls.set(started_calls.get() + 1)
        return event.id


def finish(event_id, *, usage=None, audio_seconds=None, cost_usd=None):
    incoming, outgoing, cached = token_counts(usage)
    with _factory() as db:
        event = db.get(Consumption, event_id, with_for_update=True)
        if event.status != "pending":
            return
        event.input_tokens, event.output_tokens, event.cached_tokens = incoming, outgoing, cached
        event.status = "ok"
        # Missing provider counters are unknown, never a fabricated zero.
        if event.kind != "text" or (incoming is not None and outgoing is not None):
            event.reserved_tokens = 0
        else:
            event.reserved_tokens = max(0, event.reserved_tokens - (incoming or 0) - (outgoing or 0))
        event.audio_seconds = audio_seconds if isinstance(audio_seconds, (int, float)) and audio_seconds >= 0 else None
        event.cost_usd = cost_usd
        db.commit()


def fail(event_id, *, rejected=False):
    with _factory() as db:
        event = db.get(Consumption, event_id, with_for_update=True)
        if event.status == "pending":
            event.status = "error"
            if rejected:
                event.reserved_tokens = 0
            db.commit()


def cache_hit(provider, model):
    event_id = begin("voice_cache", provider, model, "lectura_cache")
    finish(event_id)


def legacy_event(db, record):
    profile_id, actor = context.get()
    event = Consumption(profile_id=profile_id, actor=actor, provider=record.provider, model=record.model,
                        kind="text", task=record.task, status="ok", input_tokens=record.input_tokens,
                        output_tokens=record.output_tokens, cost_usd=record.cost_usd, legacy_id=record.id)
    db.add(event)
    db.flush()
    return event.id


def save_budget(scope_id, tokens, block):
    with _factory() as db:
        policy = _lock_budget(db, scope_id)
        policy.monthly_tokens, policy.block = tokens, block
        db.commit()


def report(period, profile_filter=0, profile_ids=()):
    now = datetime.now(timezone.utc)
    starts = {"mes": month_start(), "hoy": now.replace(hour=0, minute=0, second=0, microsecond=0),
              "semana": now - timedelta(days=7), "todo": datetime(1970, 1, 1, tzinfo=timezone.utc)}
    since = starts[period]
    with _factory() as db:
        query = select(Consumption).where(Consumption.created_at >= since)
        if profile_filter:
            query = query.where(Consumption.profile_id == profile_filter)
        events = db.scalars(query.order_by(Consumption.created_at.desc())).all()
        legacy = [] if profile_filter else _unassigned_legacy(db, since)
        policies = {p.scope_id: {"limit": p.monthly_tokens, "block": p.block} for p in db.scalars(select(Budget))}
        rows = {}
        provider_rows = {"openai": {}, "azure": {}}
        def row(key, store):
            return store.setdefault(key, {"profile_id": key, "calls": 0, "input": 0, "output": 0, "text_tokens": 0,
                "unknown": 0, "azure_chars": 0, "azure_units": 0, "seconds": 0.0, "audio_unknown": 0,
                "cache": 0, "cached_tokens": 0, "errors": 0, "reserved": 0, "text_cost": 0.0, "cost_unknown": 0, "adult_calls": 0, "pronunciation_seconds": 0.0, "pronunciation_calls": 0})
        for e in events:
            for r in (row(e.profile_id, rows), row(e.profile_id, provider_rows.setdefault(e.provider, {}))):
                if e.kind == "voice_cache":
                    r["cache"] += 1
                    continue
                r["calls"] += 1
                r["adult_calls"] += int(e.actor == "adult")
                r["errors"] += int(e.status == "error")
                r["input"] += e.input_tokens or 0
                r["output"] += e.output_tokens or 0
                r["cached_tokens"] += e.cached_tokens or 0
                r["reserved"] += e.reserved_tokens
                if e.kind == "text":
                    r["text_tokens"] += (e.input_tokens or 0) + (e.output_tokens or 0)
                    r["text_cost"] += e.cost_usd or 0
                    r["cost_unknown"] += int(e.cost_usd is None)
                if (e.input_tokens is None or e.output_tokens is None) and e.provider != "azure":
                    r["unknown"] += 1
                if e.kind == "azure_voice":
                    r["azure_chars"] += e.text_characters
                    r["azure_units"] += e.azure_units
                if e.kind == "pronunciation":
                    r["pronunciation_calls"] += 1
                    r["pronunciation_seconds"] += e.audio_seconds or 0
                if e.kind == "transcription":
                    if e.audio_seconds is None:
                        r["audio_unknown"] += 1
                    else:
                        r["seconds"] += e.audio_seconds
        for e in legacy:
            for r in (row(None, rows), row(None, provider_rows.setdefault(e.provider, {}))):
                r["calls"] += 1
                r["input"] += e.input_tokens
                r["output"] += e.output_tokens
                r["text_tokens"] += e.input_tokens + e.output_tokens
                r["text_cost"] += e.cost_usd
        def totalize(group):
            return {k: sum(r[k] for r in group.values()) for k in (
                "calls", "input", "output", "text_tokens", "unknown", "azure_chars", "seconds", "audio_unknown",
                "cache", "cached_tokens", "errors", "reserved", "text_cost", "cost_unknown", "pronunciation_seconds", "pronunciation_calls")}
        totals = totalize(rows)
        providers = {name: {"totals": totalize(group), "rows": group,
                           "recent": [e for e in events if e.provider == name][:25],
                           "legacy_count": sum(e.provider == name for e in legacy)}
                     for name, group in provider_rows.items()}
        scopes = set(rows) - {None}
        scopes |= set(policies) - {0}
        scopes |= set(profile_ids)
        monthly = {key: spent(db, key or None) for key in {0, *scopes}}
        return {"totals": totals, "providers": providers, "rows": list(rows.values()), "policies": policies, "monthly": monthly,
                "legacy_count": len(legacy), "recent": events[:25], "period": period, "profile_filter": profile_filter}
