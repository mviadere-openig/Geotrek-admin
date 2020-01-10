from django.conf import settings
from mapentity.registry import registry

from . import models

app_name = 'land'

urlpatterns = registry.register(models.PhysicalEdge, menu=False)
urlpatterns += registry.register(models.LandEdge, menu=settings.TREKKING_TOPOLOGY_ENABLED and settings.LANDEDGE_MODEL_ENABLED)
urlpatterns += registry.register(models.CompetenceEdge, menu=False)
urlpatterns += registry.register(models.WorkManagementEdge, menu=False)
urlpatterns += registry.register(models.SignageManagementEdge, menu=False)
