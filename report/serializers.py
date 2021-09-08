from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from taggit.models import Tag

from countries.models import Country
from report.models import Report, Sighting, PriorityChoice, SourceChoice, OverheardAtChoice, StatusChoice


class SightingSerializer(ModelSerializer):
    source = serializers.SlugRelatedField(
        slug_field='name',
        queryset=SourceChoice.objects.all(),
        allow_null=True
    )

    overheard_at = serializers.SlugRelatedField(
        slug_field='name',
        queryset=OverheardAtChoice.objects.all(),
        allow_null=True
    )

    country = serializers.SlugRelatedField(
        slug_field='iso_code',
        queryset=Country.objects.all(),
        allow_null=False
    )

    class Meta:
        model = Sighting
        fields = [
            "id",
            "source",
            "country",
            "overheard_at",
            "heard_on",
            "location",
            "address",
            "report",
        ]
        read_only_fields = ["report", "reported_via"]
        depth = 0


# class SightingWriteSerializer(ModelSerializer):
#     class Meta:
#         model = Sighting
#         fields = [
#             "source",
#             "country",
#             "overheard_at",
#             "location",
#             "address",
#             "heard_on",
#             "report",
#
#         ]
#         read_only_fields = ["report"]
#         depth = 1
#

class TagSerializer(serializers.RelatedField):
    def to_representation(self, value):
        return value.name

    class Meta:
        model = Tag


class ReportSerializer(ModelSerializer):
    sighting_count = serializers.SerializerMethodField()
    first_sighting = serializers.SerializerMethodField()
    tags = TagSerializer(read_only=True, many=True)

    country = serializers.SlugRelatedField(
        slug_field='iso_code',
        queryset=Country.objects.all(),
        allow_null=False
    )

    status = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True
    )

    priority = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "tags",
            "country",
            "occurred_on",
            "location",
            "tags",
            "address",
            "sighting_count",
            "first_sighting",
            "resolution",
            "status",
            "priority",
        ]
        read_only_fields = ["id", "resolution", "status", "priority"]

    def get_sighting_count(self, obj):
        count = Sighting.objects.filter(report=obj).count()
        return count

    def get_first_sighting(self, obj):
        sighting = Sighting.objects.filter(report=obj, is_first_sighting=True).first()
        serializer = SightingSerializer(sighting)
        return serializer.data


