from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TaxonomyFacet, TaxonomyValue
from .serializers import TaxonomyFacetSerializer, TaxonomyValueSerializer


class TaxonomyListView(generics.ListAPIView):
    """GET /api/taxonomy/ -- every facet with its allowed values, for both the
    filter sidebar and the taxonomy admin screen."""

    queryset = TaxonomyFacet.objects.prefetch_related("values").all()
    serializer_class = TaxonomyFacetSerializer
    pagination_class = None


class TaxonomyValueListCreateView(APIView):
    """POST /api/taxonomy/<facet_key>/values/ -- add a new allowed value."""

    def post(self, request, facet_key):
        facet = get_object_or_404(TaxonomyFacet, key=facet_key)
        serializer = TaxonomyValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(facet=facet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TaxonomyValueDetailView(APIView):
    """PATCH/DELETE /api/taxonomy/<facet_key>/values/<value>/"""

    def patch(self, request, facet_key, value):
        obj = get_object_or_404(TaxonomyValue, facet__key=facet_key, value=value)
        serializer = TaxonomyValueSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, facet_key, value):
        obj = get_object_or_404(TaxonomyValue, facet__key=facet_key, value=value)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
