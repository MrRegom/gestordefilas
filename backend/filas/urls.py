from django.urls import path
from django.views.generic import TemplateView

from . import api_totem

urlpatterns = [
    path("api/totem/config/", api_totem.ConfigTotem.as_view()),
    path("api/totem/tickets/", api_totem.EmitirTicketTotem.as_view()),
    path("api/totem/latido/", api_totem.LatidoTotem.as_view()),
    path("totem/", TemplateView.as_view(template_name="filas/totem.html"), name="totem"),
]
