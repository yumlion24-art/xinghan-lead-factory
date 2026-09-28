from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from lead_factory.models import Account, Evidence, SourcePage
from lead_factory.schemas import AccountObservation


def upsert_observation(
    session: Session, observation: AccountObservation, *, search_task_id: str | None = None
) -> Account:
    account = session.scalar(
        select(Account).where(Account.normalized_domain == observation.normalized_domain)
    )
    if account is None:
        account = Account(
            display_name=observation.display_name,
            normalized_domain=observation.normalized_domain,
        )
        session.add(account)
        session.flush()

    account.display_name = observation.display_name or account.display_name
    account.website_url = observation.website_url
    account.country = observation.country or account.country
    account.industry = observation.industry or account.industry
    account.company_type = observation.company_type or account.company_type
    account.description = observation.description or account.description
    account.scale_signals = list(dict.fromkeys([*account.scale_signals, *observation.scale_signals]))
    account.contact_routes = list(observation.contact_routes or account.contact_routes)

    for item in observation.evidence:
        page = session.scalar(select(SourcePage).where(SourcePage.canonical_url == item.source_url))
        if page is None:
            page = SourcePage(
                account=account,
                url=item.source_url,
                canonical_url=item.source_url,
                retrieval_status="collected",
                content_hash=hashlib.sha256(item.excerpt.encode()).hexdigest(),
                extracted_text=item.excerpt,
                search_task_id=search_task_id,
            )
            session.add(page)
            session.flush()
        existing = session.scalar(
            select(Evidence).where(
                Evidence.account_id == account.id,
                Evidence.source_url == item.source_url,
                Evidence.excerpt == item.excerpt,
            )
        )
        if existing is None:
            session.add(
                Evidence(
                    account=account,
                    source_page=page,
                    signal_type=item.signal_type,
                    excerpt=item.excerpt,
                    source_url=item.source_url,
                    confidence=item.confidence,
                )
            )
    session.flush()
    return account
