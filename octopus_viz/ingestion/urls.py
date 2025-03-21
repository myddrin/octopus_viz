from django.urls import path

from ingestion.views import (
    home,
    graphs,
    configuration,
    ingestion,
)

urlpatterns = [
    path('', home.HomeView.as_view(), name='home'),
    path('monthly/', graphs.MonthlyConsumptionGraphView.as_view(), name='monthly_consumption_graph'),
    path('tariff/', graphs.MonthlyTariffGraphView.as_view(), name='monthly_tariff_graph'),
    # data calls
    path('monthly_data/', graphs.MonthlyGraphData.as_view(), name='monthly_graph_data'),
    path('tariff_data/', graphs.TariffGraphData.as_view(), name='tariff_graph_data'),
    # configuration forms
    path('config/new_flux', configuration.AddOctopusTariffView.as_view(), name='add_new_flux_form'),
    path('config/new_flux/process', configuration.ProcessOctopusTariffView.as_view(), name='process_new_flux_form'),
    # ingestion APIs
    path('ingestion/octopus', ingestion.IngestOctopus.as_view(), name='ingestion_octopus'),
]
