"""Où en est un sondage dans la file des synthèses (EPF-MDE/OceENS#147).

La file est la table `summaries` : `http_status` 0 est en attente, 200 est
fait, toute autre valeur (NULL compris) est un échec. Le daemon prend les
lignes en attente sans ordre défini : le temps restant compte donc toute la
file, de tous les sondages, pas seulement les lignes du sondage.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, case, func, select

from oceens.models import Summary

# Hypothèse B du Design Document (EPF-MDE/OceENS#117) : durée typique d'une
# synthèse, mesurée le 25 septembre 2026 (18,6 s pour un travail médian).
SECONDS_PER_SUMMARY = 20

STATUS_PENDING = 0
STATUS_DONE = 200


@dataclass(frozen=True)
class SurveyProgress:
    """Ce que la file répond pour un sondage.

    `estimated_time_left` est None quand le sondage n'a rien en attente : il
    n'y a alors rien à attendre, même si d'autres sondages sont dans la file.
    """

    done: int
    total: int
    errors: int
    estimated_time_left: Optional[timedelta]

    @property
    def pending(self) -> int:
        return self.total - self.done - self.errors

    @property
    def finished(self) -> bool:
        return self.total > 0 and self.pending == 0


def progress(session: Session, survey_id: int) -> SurveyProgress:
    """Avancement d'un sondage et temps restant estimé, lus dans la file."""
    done, total, errors = session.exec(
        select(
            func.count(case((Summary.http_status == STATUS_DONE, 1))),
            func.count(Summary.summary_id),
            func.count(
                case(
                    (Summary.http_status == STATUS_PENDING, None),
                    (Summary.http_status == STATUS_DONE, None),
                    else_=1,
                )
            ),
        ).where(Summary.survey_id == survey_id)
    ).one()

    estimated_time_left = None
    if total - done - errors > 0:
        pending_in_queue = session.exec(
            select(func.count(Summary.summary_id)).where(
                Summary.http_status == STATUS_PENDING
            )
        ).one()
        estimated_time_left = timedelta(seconds=pending_in_queue * SECONDS_PER_SUMMARY)

    return SurveyProgress(
        done=done,
        total=total,
        errors=errors,
        estimated_time_left=estimated_time_left,
    )
