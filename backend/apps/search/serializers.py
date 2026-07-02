from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=False, trim_whitespace=True)
    filters = serializers.DictField(required=False, default=dict)
    top_k = serializers.IntegerField(required=False, default=20, min_value=1)
    min_confidence = serializers.FloatField(required=False, default=0.0)

    def validate_query(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("query must not be blank.")
        return value


class SearchResultSerializer(serializers.Serializer):
    video_id = serializers.CharField()
    start_s = serializers.FloatField()
    end_s = serializers.FloatField()
    confidence = serializers.FloatField()
    matched_text = serializers.CharField(allow_blank=True)
    video = serializers.DictField()
