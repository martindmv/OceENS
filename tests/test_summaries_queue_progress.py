"""`progress` : où en est un sondage dans la file des synthèses, avec un temps restant estimé.

Les chiffres viennent du Design Document (EPF-MDE/OceENS#117) : 45 synthèses par
sondage (A), 20 s par synthèse (B), 10 programmes le même soir (C).
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.summaries_queue import progress

JOBS_PER_SURVEY = 45
SURVEYS_ON_A_CAMPAIGN_EVENING = 10


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def queue_pending_jobs(session, survey_id, count):
    for _ in range(count):
        session.add(Summary(survey_id=survey_id, http_status=0))
    session.commit()


def test_a_campaign_evening_shows_two_and_a_half_hours_not_a_bare_count(session):
    for survey_id in range(1, SURVEYS_ON_A_CAMPAIGN_EVENING + 1):
        queue_pending_jobs(session, survey_id, JOBS_PER_SURVEY)

    survey_progress = progress(session, survey_id=1)

    assert survey_progress.done == 0
    assert survey_progress.total == 45
    assert survey_progress.estimated_time_left == timedelta(hours=2, minutes=30)
