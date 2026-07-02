from django.urls import path

from . import views

urlpatterns = [
    path("", views.TaxonomyListView.as_view(), name="taxonomy-list"),
    path(
        "<slug:facet_key>/values/",
        views.TaxonomyValueListCreateView.as_view(),
        name="taxonomy-value-list-create",
    ),
    path(
        "<slug:facet_key>/values/<slug:value>/",
        views.TaxonomyValueDetailView.as_view(),
        name="taxonomy-value-detail",
    ),
]
