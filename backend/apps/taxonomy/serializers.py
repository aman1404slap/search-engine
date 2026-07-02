from rest_framework import serializers

from .models import TaxonomyFacet, TaxonomyValue


class TaxonomyValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxonomyValue
        fields = ["id", "value", "label", "order"]


class TaxonomyFacetSerializer(serializers.ModelSerializer):
    values = TaxonomyValueSerializer(many=True, read_only=True)

    class Meta:
        model = TaxonomyFacet
        fields = ["id", "key", "label", "multi_select", "order", "values"]
