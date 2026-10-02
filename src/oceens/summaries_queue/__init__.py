"""La file des synthèses : ce que les pages lisent de l'avancement d'un sondage.

Ce fichier est la surface publique du paquet. Les dashboards demandent
`progress(session, survey_id)` au lieu de compter eux-mêmes les synthèses
faites, en attente et en échec, et le template n'a plus à décider seul ce que
« terminé » veut dire.
"""

from oceens.summaries_queue.progress import SurveyProgress, progress

__all__ = ["SurveyProgress", "progress"]
