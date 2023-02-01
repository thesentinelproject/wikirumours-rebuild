from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from taggit.models import Tag
import json
from countries.models import Country
from report.models import Report, Sighting, PriorityChoice, SourceChoice, OverheardAtChoice, StatusChoice, Comment, WatchlistedReport, Domain, NotificationHistoryData
import re
from newapi.jwt_token_auth import get_token, decrypt_token


class SightingSerializer(ModelSerializer):
    country_name = serializers.SerializerMethodField('get_sighting_country_name')
    lat_long = serializers.SerializerMethodField('get_sighting_lat_long')
    country_iso = serializers.SerializerMethodField('get_country_iso')
    reported_via_name = serializers.SerializerMethodField('get_reported_via_name')
    source = serializers.SlugRelatedField(
        slug_field='name',
        queryset=SourceChoice.objects.all(),
        allow_null=True,
        required=False
    )

    overheard_at = serializers.SlugRelatedField(
        slug_field='name',
        queryset=OverheardAtChoice.objects.all(),
        allow_null=True,
        required=False
    )

    country = serializers.SlugRelatedField(
        slug_field='iso_code',
        queryset=Country.objects.all(),
        allow_null=False
    )

    def get_sighting_country_name(self, obj):
        if obj.country:
            return obj.country.name
        else:
            return None

    def get_country_iso(self, obj):
        if obj.country:
            return obj.country.iso_code
        else:
            return None

    class Meta:
        model = Sighting
        fields = [
            "id",
            "source",
            "country_name",
            "country_iso",
            "country",
            "overheard_at",
            "heard_on",
            "lat_long",
            "location",
            "address",
            "report",
            "reported_via",
            "reported_via_name",
            "is_first_sighting",
        ]
        read_only_fields = ["report", "reported_via"]
        depth = 0

    def get_reported_via_name(self, obj):
        if obj.reported_via:
            return obj.reported_via.name
        else:
            return None

    def get_sighting_lat_long(self, obj):
        try:
            sight_loc = obj.location
            try:
                point_value = sight_loc
                point_value2 = str(point_value)
                lat_long = re.findall('\(([^)]+)', point_value2)
                lat_long2 = str(lat_long)[1:-1]
                lat_long3 = lat_long2.replace("'","")
                lat_long4 = lat_long3.replace(" ",",")
                return lat_long4
                
            except:
                return None
        except Exception as e:
            print("here....", e)


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

# class TagSerializer(serializers.RelatedField):
#     def to_representation(self, value):
#         return value.name

#     class Meta:
#         model = Tag

class StringListField(serializers.ListField): # get from http://www.django-rest-framework.org/api-guide/fields/#listfield
    child = serializers.CharField()

    def to_representation(self, data):
        return ' '.join(data.values_list('name', flat=True))


class ReportSerializer(ModelSerializer):
    first_sighting = serializers.SerializerMethodField('get_first_sighting')
    sighting_count = serializers.SerializerMethodField('get_sighting_count')
    country_name = serializers.SerializerMethodField('get_country_name')
    country_iso = serializers.SerializerMethodField('get_country_iso')
    sighting_country_name = serializers.SerializerMethodField('get_sighting_country_name')
    sighting_country_iso = serializers.SerializerMethodField('get_sighting_country_iso')
    reported_via_name = serializers.SerializerMethodField('get_reported_via_name')
    lat_long = serializers.SerializerMethodField('get_lat_long')
    sighting_lat_long = serializers.SerializerMethodField('get_sighting_lat_long')
    comment_count = serializers.SerializerMethodField('get_comment_count')
    is_watchlisted = serializers.SerializerMethodField('get_is_watchlisted')
    
    # tags = TagSerializer(read_only=True, many=True)
    tags = StringListField()

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
            "address",
            "assigned_to",
            "sighting_count",
            "first_sighting",
            "resolution",
            "status",
            "priority",
            "domain",
            "country_name",
            "country_iso",
            "sighting_country_name",
            "sighting_country_iso",
            "reported_via_name",
            "lat_long",
            "sighting_lat_long",
            "comment_count",
            "is_watchlisted",
            "emergency_alert",
        ]
        read_only_fields = ["id","status", "priority","domain"]

    def get_sighting_count(self, obj):
        count = Sighting.objects.filter(report=obj).count()
        return count

    def get_first_sighting(self, obj):
        sighting = Sighting.objects.filter(report=obj, is_first_sighting=True).first()
        serializer = SightingSerializer(sighting)
        return serializer.data

    def get_country_name(self, obj):
        if obj.country:
            return obj.country.name
        else:
            return None

    def get_country_iso(self, obj):
        if obj.country:
            return obj.country.iso_code
        else:
            return None

    def get_sighting_country_name(self, obj):
        if obj.country:
            return obj.country.name
        else:
            return None

    def get_sighting_country_iso(self, obj):
        if obj.country:
            return obj.country.iso_code
        else:
            return None
    
    def get_reported_via_name(self, obj):
        try:
            sighting = Sighting.objects.get(report=obj, is_first_sighting=True)
        except:
            sighting = None
        if not sighting:
            return None
        else:
            if sighting.reported_via:
                return sighting.reported_via.name
            else:
                return None

    def get_lat_long(self, obj):
        point_value = obj.location
        point_value2 = str(point_value)
        lat_long = re.findall('\(([^)]+)', point_value2)
        lat_long2 = str(lat_long)[1:-1]
        lat_long3 = lat_long2.replace("'","")
        lat_long4 = lat_long3.replace(" ",",")
        return lat_long4

    def get_sighting_lat_long(self, obj):
        sighting = Sighting.objects.filter(report=obj, is_first_sighting=True).first()
        try:
            if sighting:
                point_value = sighting.location
                point_value2 = str(point_value)
                lat_long = re.findall('\(([^)]+)', point_value2)
                lat_long2 = str(lat_long)[1:-1]
                lat_long3 = lat_long2.replace("'","")
                lat_long4 = lat_long3.replace(" ",",")
                return lat_long4
            else:
                return None
        except:
            return None

    def get_comment_count(self, obj):
        comment_count = Comment.objects.filter(report=obj).count()
        return comment_count

    def get_is_watchlisted(self, obj):
        try:
            token = self.context['request'].META.get("HTTP_AUTHORIZATION")
            user = decrypt_token(token)
            try:
                WatchlistedReport.objects.get(report=obj,user=user)
                is_watchlisted = 1
                return is_watchlisted
            except:
                return 0
        except:
            return 0

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        instance = super(ReportSerializer, self).create(validated_data)
        instance.tags.set(*tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        instance = super(ReportSerializer, self).create(validated_data)
        instance.tags.set(*tags)
        return instance



class NotificationSerializer(serializers.ModelSerializer):
    time = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ")
    class Meta:
        model = NotificationHistoryData
        fields=("id","notification_type","text","time")



