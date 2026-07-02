from django.db import models


class TaxonomyFacet(models.Model):
    """A filterable dimension, e.g. "request" or "target_entity"."""

    key = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=150)
    multi_select = models.BooleanField(
        default=False,
        help_text="True for facets that can hold several values per video (tags), "
        "False for single-select facets stored directly on Video.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "key"]

    def __str__(self):
        return self.key


class TaxonomyValue(models.Model):
    """A single allowed value within a facet, e.g. request="identify_item"."""

    facet = models.ForeignKey(TaxonomyFacet, related_name="values", on_delete=models.CASCADE)
    value = models.SlugField(max_length=150)
    label = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "value"]
        unique_together = ("facet", "value")

    def __str__(self):
        return f"{self.facet.key}:{self.value}"
