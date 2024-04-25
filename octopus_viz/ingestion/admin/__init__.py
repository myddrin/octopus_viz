from django.contrib import admin

from ingestion import models
from ._views import MPANAdminView, APIKeyAdminView, MeterAdminView, ConsumptionAdminView, RateAdminView, TariffAdminView

admin.site.register(models.APIKey, admin_class=APIKeyAdminView)
admin.site.register(models.MPAN, admin_class=MPANAdminView)
admin.site.register(models.Meter, admin_class=MeterAdminView)
admin.site.register(models.Tariff, admin_class=TariffAdminView)
admin.site.register(models.Rate, admin_class=RateAdminView)
admin.site.register(models.Consumption, admin_class=ConsumptionAdminView)
