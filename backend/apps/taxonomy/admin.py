from django.contrib import admin

from .models import TaxonomyFacet, TaxonomyValue


class TaxonomyValueInline(admin.TabularInline):
    model = TaxonomyValue
    extra = 1


@admin.register(TaxonomyFacet)
class TaxonomyFacetAdmin(admin.ModelAdmin):
    list_display = ["key", "label", "multi_select", "order"]
    inlines = [TaxonomyValueInline]


@admin.register(TaxonomyValue)
class TaxonomyValueAdmin(admin.ModelAdmin):
    list_display = ["facet", "value", "label", "order"]
    list_filter = ["facet"]
    ordering = ["facet__order", "order"]
