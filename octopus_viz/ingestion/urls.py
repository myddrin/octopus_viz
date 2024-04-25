from django.urls import path

from ingestion.views import home, graphs

urlpatterns = [
    path('', home.IndexView.as_view(), name='index'),
    path('monthly/', home.MonthlyConsumptionGraphView.as_view(), name='monthly_consumption_graph'),
    path('tariff/', home.MonthlyTariffGraphView.as_view(), name='monthly_tariff_graph'),
    # data calls
    path('monthly_data/', graphs.MonthlyGraphData.as_view(), name='monthly_graph_data'),
    path('tariff_data/', graphs.TariffGraphData.as_view(), name='tariff_graph_data'),
]
