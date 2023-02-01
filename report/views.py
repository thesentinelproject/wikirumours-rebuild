import datetime
import heapq
import json
import re
from datetime import timedelta
from heapq import heappush, nlargest
from itertools import combinations

import magic
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext_lazy
from django.views.decorators.http import require_http_methods
from geopy.geocoders import Nominatim
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action as drf_action
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from countries.models import Country
from users.authentication import ApiAuthentication
from users.emails import new_report_alert, emergency_report_alert
from users.models import User
from wikirumours.base_settings import GOOGLE_MAPS_KEY, MAPBOX_API_KEY
from .forms import (
    AddReportForm,
    EndUserSightingForm,
    AdminReportForm,
    CommunityLiaisonForm,
    AddSightingForm, ReportFilterForm,
)
from .models import *
from .serializers import *
from .utils import get_tags_from_title, get_location_array 
from django.contrib.sites.shortcuts import get_current_site
from django.template.context_processors import csrf
from logs.utils import *
from newapi.jwt_token_auth import get_token, decrypt_token
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.core import serializers as se
from .send_notification import FCMPushView, add_mobile_token, delete_mobile_token, update_mobile_token
from newapi.models import LoginDetail
from fcm_django.models import FCMDevice


# Create your views here.
def index(request):
    request_domain = get_current_site(request).domain
    reports = Report.objects.annotate(count=Count("sighting"))
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
        if not domain.is_root_domain:
            reports = reports.filter(domain=domain)

    # filters
    search_term = request.GET.get("search_term")
    if search_term:
        reports = reports.filter(title__icontains=search_term)

    status = request.GET.get("status")
    if status:
        reports = reports.filter(status__name=status)

    priority = request.GET.get("priority")
    if priority:
        reports = reports.filter(priority__name=priority)

    country = request.GET.get("country")
    if country:
        reports = reports.filter(country__name=country)

    # sort
    sort_by = request.GET.get("sort_by")

    if sort_by == "most_sighted":
        reports = reports.annotate(count=Count("sighting")).order_by("-count")
    elif sort_by == "recently_occurred":
        reports = reports.order_by('-occurred_on')
    else:
        reports = reports.order_by('-updated_at')

    # filter form
    form = ReportFilterForm(request.GET)

    paginator = Paginator(reports, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj,
               "reports": page_obj.object_list,
               "search_term": search_term or '',
               "form": form}

    return TemplateResponse(request, "report/reports.html", context)


class StandardResultPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 1000


class ReportViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    authentication_classes = (
        SessionAuthentication,
        ApiAuthentication,
    )
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    http_method_names = ["get", "post", "put"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        username = request.headers.get("username")
        api_key = request.headers.get("Api-key")

        user = User.objects.filter(username=username, api_key=api_key).first()

        # check if user is permitted to make POST requests
        if not user.api_post_access:
            return HttpResponseForbidden("You have insufficient permissions")
        request_domain = get_current_site(request).domain
        domain_query = Domain.objects.filter(domain=request_domain)
        if domain_query.exists():
            domain = domain_query.first()
        else:
            domain = Domain.objects.all().first()
        latlong = None
        report_address = None
        locator = Nominatim(user_agent="wikirumours")
        if request.data.get("report_location"):
            location = request.data.get("report_location").split(",")
            report_latlong = "{},{}".format(location[0], location[1])

            latlong = Point(float(location[1]), float(location[0]))
            try:
                report_address = locator.reverse(report_latlong)

            except Exception:

                report_address = report_latlong

        report_country = Country.objects.filter(
            iso_code=request.data.get("country")
        ).first()

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            report = serializer.save(
                reported_by=user,
                domain=domain,
                country=report_country,
                location=latlong,
                address=report_address,
            )
        sighting_serializer = SightingSerializer(data=request.data)
        latlong_sighting = None
        sighting_address = None
        if request.data.get("sighting_location"):
            location = request.data.get("sighting_location").split(",")
            sighting_latlong = "{},{}".format(location[0], location[1])
            latlong_sighting = Point(float(location[1]), float(location[0]))
            try:
                sighting_address = locator.reverse(sighting_latlong)
            except Exception:

                sighting_address = sighting_latlong

        sighting_country = Country.objects.filter(
            iso_code=request.data.get("sighting_country")
        ).first()
        if sighting_serializer.is_valid(raise_exception=True):
            sighting_serializer.save(
                user=user,
                report=report,
                is_first_sighting=True,
                country=sighting_country,
                location=latlong_sighting,
                address=sighting_address,
            )
        log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Create Report','report':report}
        create_user_log(log_data)
        headers = self.get_success_headers(sighting_serializer.data)
        data = {"report": serializer.data}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        print("here*********")
        request_domain = get_current_site(request).domain
        domain_query = Domain.objects.filter(domain=request_domain)
        if domain_query.exists():
            domain = domain_query.first()
        else:
            domain = Domain.objects.all().first()
        queryset = Report.objects.all()

        if not domain.is_root_domain:
            queryset = queryset.filter(domain=domain)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        report_serializer = self.get_serializer(instance)
        return Response(report_serializer.data)

    def update(self, request, *args, **kwargs):
        username = request.headers.get("username")
        api_key = request.headers.get("Api-key")

        user = User.objects.filter(username=username, api_key=api_key).first()

        # check if user is permitted to make POST requests
        if not user.api_post_access:
            return HttpResponseForbidden("You have insufficient permissions")

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.reported_by == user:
            report_country = Country.objects.filter(
                iso_code=request.data.get("country")
            ).first()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            locator = Nominatim(user_agent="wikirumours")
            if request.data.get("report_location"):
                location = request.data.get("report_location").split(",")
                report_latlong = "{},{}".format(location[0], location[1])
                latlong = Point(float(location[1]), float(location[0]))
                try:
                    report_address = locator.reverse(report_latlong)
                except Exception:
                    report_address = report_latlong
                if serializer.is_valid(raise_exception=True):
                    report = serializer.save(
                        country=report_country, location=latlong, address=report_address
                    )
            else:

                if serializer.is_valid(raise_exception=True):
                    report = serializer.save(country=report_country)

            sighting = Sighting.objects.filter(
                report=report, is_first_sighting=True
            ).first()
            sighting_serializer = SightingSerializer(
                sighting, data=request.data, partial=partial
            )
            sighting_country = Country.objects.filter(
                iso_code=request.data.get("sighting_country")
            ).first()
            if request.data.get("sighting_location"):
                location = request.data.get("sighting_location").split(",")
                sighting_latlong = "{},{}".format(location[0], location[1])
                latlong_sighting = Point(float(location[1]), float(location[0]))
                try:
                    sighting_address = locator.reverse(sighting_latlong)
                except Exception:
                    sighting_address = sighting_latlong

            if sighting_serializer.is_valid(raise_exception=True):
                sighting_serializer.save(
                    country=sighting_country,
                    location=latlong_sighting,
                    address=sighting_address,
                )
            else:
                if sighting_serializer.is_valid(raise_exception=True):
                    sighting_serializer.save(country=sighting_country)
            headers = self.get_success_headers(serializer.data)
            # data = {'report': serializer.data, 'sighting': sighting_serializer.data}
            log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Update Report','report':report,'sighting':sighting}
            create_user_log(log_data)
            return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(
                {"You don't have permission to update this report"},
                status=status.HTTP_403_FORBIDDEN,
            )

    @drf_action(detail=True, methods=["GET"])
    def sightings(self, request, pk=None):
        instance = self.get_object()
        queryset = Sighting.objects.filter(report=instance)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SightingSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SightingSerializer(queryset, many=True)
        return Response(serializer.data)


class SightingViewSet(viewsets.ModelViewSet):
    queryset = Sighting.objects.all()
    serializer_class = SightingSerializer
    http_method_names = ["get", "post", "put","delete"]

    def retrieve(self,request, pk=None):
        sighting_data = []
        sighting_obj = Sighting.objects.filter(report__id=pk).order_by('-id')
        for detail in sighting_obj:
            if detail.country:
                country_name = detail.country.name
                country_iso = detail.country.iso_code
            else:
                country_name = None
                country_iso = None
            if detail.source:
                source = detail.source.name
            else:
                source = None
            if detail.overheard_at:
                print("why.....", detail)
                overheard_at = detail.overheard_at.name
            else:
                overheard_at = None
            if detail.location:
                pass
            else:
                detail.location = None
            if detail.reported_via:
                reported_via = detail.reported_via.name
            else:
                reported_via = None
            if detail.address:
                pass
            else:
                detail.address = None
            try:
                point_value = detail.location
                point_value2 = str(point_value)
                lat_long = re.findall('\(([^)]+)', point_value2)
                lat_long2 = str(lat_long)[1:-1]
                lat_long3 = lat_long2.replace("'","")
                lat_long4 = lat_long3.replace(" ",",")
            except:
                lat_long4 = None
            sighting_data.append({"id":detail.id,"source":source,"country_name":country_name,"country_iso":country_iso,"overheard_at":overheard_at,
            "heard_on":detail.heard_on, "lat_long":lat_long4,"address":detail.address,"report":detail.report.id,"reported_via_name":reported_via,"is_first_sighting":detail.is_first_sighting})

        return Response({"status":1,"message":"Sighting Listing",'data':sighting_data})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            # check if user is permitted to make POST requests
            if not user.is_verified:
                return Response({"status": 0, "message": "You have insufficient permissions!"})
            report = request.data["report"]
            
            try:
                report = Report.objects.get(id=report)
            except:
                return Response({"status": 0, "message": "Please provide valid report id."})
            sighting_country = Country.objects.filter(
                iso_code=request.data.get("country")
            ).first()
            serializer = self.get_serializer(data=request.data)
            latlong = None
            # sighting_address = None
            sighting_address = request.data['address'] if request.data.get('address') else None
            sighting_location = request.data['location'] if request.data.get('location') else None
            locator = Nominatim(user_agent="wikirumours")

            if sighting_address:
                if sighting_location:
                    location = request.data.get("location").split(",")
                    latlong = Point(float(location[1]), float(location[0]))
                else:
                    try:
                        getLoc = locator.geocode(sighting_address)
                        latlong = Point(float(getLoc.longitude), float(getLoc.latitude))
                        if not latlong:
                            latlong = Point(float(1), float(1))
                    except:
                        latlong = Point(float(1), float(1))
                # if request.data.get("report_location"):
                # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                # report_latlong = "{},{}".format(location[0], location[1])

                # latlong = Point(float(location[1]), float(location[0]))
                # try:
                #     report_address = locator.reverse(report_latlong)

                # except Exception:

                #     report_address = report_latlong
            else:
                if request.data.get("location"):
                    location = request.data.get("location").split(",")
                    sighting_latlong = "{},{}".format(location[0], location[1])

                    latlong = Point(float(location[1]), float(location[0]))
                    try:
                        sighting_address = locator.reverse(sighting_latlong)

                    except Exception:

                        sighting_address = sighting_latlong

            # if request.data.get("location"):
            #     location = request.data.get("location").split(",")
            #     sighting_latlong = "{},{}".format(location[0], location[1])
            #     latlong = Point(float(location[1]), float(location[0]))
            #     try:
            #         sighting_address = locator.reverse(sighting_latlong)
            #     except Exception:
            #         sighting_address = sighting_latlong
            if serializer.is_valid(raise_exception=True):
                sighting = serializer.save(
                    user=user,
                    report=report,
                    is_first_sighting=False,
                    location=latlong,
                    address=sighting_address,
                )
            else:
                sighting = None
            if "user" in serializer.errors:
                return Response({"status": 0, "message": "user - " + serializer.errors['user'][0]})
            if "report" in serializer.errors:
                return Response({"status": 0, "message": "report - " + serializer.errors['report'][0]})
            if "location" in serializer.errors:
                return Response({"status": 0, "message": "location - " + serializer.errors['location'][0]})
            if "address" in serializer.errors:
                return Response({"status": 0, "message": "address - " + serializer.errors['address'][0]})
            sighting_serializer = SightingSerializer(data=request.data)
            
            log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Create Sighting','report':report,'sighting':sighting}
            create_user_log(log_data)
            headers = self.get_success_headers(serializer.data)
            data = {"sighting": serializer.data}
            return Response({"status": 1, "message": "Sighting created successfully.", "data":data})
        else:
            return Response({"status": 0, "message": "Invalid access token!"})

    def update(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            if user.role == "Admin" or user.role == "Moderator":
                partial = kwargs.pop("partial", True)
                instance = self.get_object()
                # check if user is permitted to make POST requests
                if not user.is_verified:
                    return Response({"status": 0, "message": "You have insufficient permissions!"})

                # if instance.user == user:

                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial
                )
                sighting_address = request.data['address'] if request.data.get('address') else None
                sighting_location = request.data['location'] if request.data.get('location') else None
                locator = Nominatim(user_agent="wikirumours")
                if request.data.get("location"):
                    if sighting_address:
                        if sighting_location:
                            location = request.data.get("location").split(",")
                            latlong = Point(float(location[1]), float(location[0]))
                        else:
                            try:
                                getLoc = locator.geocode(sighting_address)
                                latlong = Point(float(getLoc.longitude), float(getLoc.latitude))
                                if not latlong:
                                    latlong = Point(float(1), float(1))
                            except:
                                latlong = Point(float(1), float(1))
                        # if request.data.get("report_location"):
                        # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                        # report_latlong = "{},{}".format(location[0], location[1])

                        # latlong = Point(float(location[1]), float(location[0]))
                        # try:
                        #     report_address = locator.reverse(report_latlong)

                        # except Exception:

                        #     report_address = report_latlong
                    else:
                        if request.data.get("location"):
                            location = request.data.get("location").split(",")
                            sighting_latlong = "{},{}".format(location[0], location[1])

                            latlong = Point(float(location[1]), float(location[0]))
                            try:
                                sighting_address = locator.reverse(sighting_latlong)

                            except Exception:

                                sighting_address = sighting_latlong
                    # location = request.data.get("location").split(",")
                    # sighting_latlong = "{},{}".format(location[0], location[1])
                    # latlong = Point(float(location[1]), float(location[0]))
                    # try:
                    #     sighting_address = locator.reverse(sighting_latlong)
                    # except Exception:
                    #     sighting_address = sighting_latlong

                    if serializer.is_valid(raise_exception=True):
                        sighting_country = Country.objects.filter(
                            iso_code=request.data.get("country")
                        ).first()
                        sighting = serializer.save(
                            country=sighting_country,
                            location=latlong,
                            address=sighting_address,
                        )
                    if "country" in serializer.errors:
                        return Response({"status": 0, "message": "country - " + serializer.errors['country'][0]})
                    if "location" in serializer.errors:
                        return Response({"status": 0, "message": "location - " + serializer.errors['location'][0]})
                    if "address" in serializer.errors:
                        return Response({"status": 0, "message": "address - " + serializer.errors['address'][0]})
                else:
                    if serializer.is_valid(raise_exception=True):
                        sighting_country = Country.objects.filter(
                            iso_code=request.data.get("country")
                        ).first()
                        sighting = serializer.save(country=sighting_country)
                    if "country" in serializer.errors:
                        return Response({"status": 0, "message": "country - " + serializer.errors['country'][0]})
                    
                headers = self.get_success_headers(serializer.data)
                log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Update Sighting','report':sighting.report,'sighting':sighting}
                create_user_log(log_data)
                data = {"sighting": serializer.data}
                return Response({"status": 1, "message": "Sighting updated successfully.", "data":data})
                # else:
                #     return Response({"status": 0, "message":"You don't have permission to update this report"})
            else:
                return Response({"status": 0, "message":"You don't have permission to update this report"})
        else:
            return Response({"status": 0, "message": "Invalid access token!"})


    def destroy(self, request, pk=None):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            if user.role == "Admin" or user.role == "Moderator":
                try:
                    delete_sighting = Sighting.objects.get(id=pk)
                    delete_sighting.delete()
                    return Response({"status":1,"message":"Sighting deleted successfully"})
                except:
                    return Response({"status":0,"message":"provide valid sighting id"})
            else:
                return Response({"status":0,"message":"you have insufficient permission!"})
        else:
            return Response({"status":0,"message":"invalid access token"})


@login_required
def new_report(request):
    return render(request, "report/new_report.html")



@login_required
def check_report_presence(request):
    title = request.POST["title"]
    request_domain = get_current_site(request).domain

    if title == "":
        error_msg = ugettext_lazy("Title of report cannot be empty")
        return render(
            request,
            "report/new_report.html",
            context={"error": error_msg},
        )

    # get similar_reports
    tags = get_tags_from_title(title)
    base_query = Q()
    if len(tags) < 2:
        matching_reports = None
    else:
        for combination in (combinations(tags, 2)):
            base_query = base_query | Q(Q(title__icontains=combination[0]) & Q(title__icontains=combination[1]))
        domain_query = Domain.objects.filter(domain=request_domain)
        if domain_query.exists():
            domain = domain_query.first()
        else:
            domain = Domain.objects.all().first()
        matching_reports = Report.objects.filter(base_query)

        if not domain.is_root_domain:
            matching_reports = matching_reports.filter(domain=domain)

    if matching_reports is None or matching_reports.count() == 0:
        report_form_initial = {"title": title, "tags": ','.join(get_tags_from_title(title))}
        if request.user.role == User.END_USER:
            report_form = AddReportForm(initial=report_form_initial)
            sighting_form = EndUserSightingForm()
        elif request.user.role == User.SUPPORT:
            report_form = AddReportForm(initial={"title": title})
            sighting_form = AddSightingForm()
        elif request.user.role == User.ADMIN or request.user.role == User.MODERATOR:
            report_form = AdminReportForm(initial={"title": title})

            # allow to assign to admins, moderators and community liaisons of this domain
            report_form.fields["assigned_to"].queryset = User.objects.filter(
                role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
                role_domains=Domain.objects.filter(domain=request_domain).first(),
            )
            sighting_form = AddSightingForm()
        else:
            report_form = CommunityLiaisonForm(
                initial={"title": title}
            )
            sighting_form = AddSightingForm()

        context = {"report_form": report_form, "sighting_form": sighting_form}
        return render(request, "report/add_report.html", context)
    else:
        return render(
            request, "report/matching_report.html", {"title": title, "reports": matching_reports}
        )


@login_required
def add_report(request):
    title = request.POST["title"]
    if request.user.role == User.END_USER:
        report_form = AddReportForm(initial={"title": title})
        sighting_form = EndUserSightingForm()
    elif request.user.role == User.SUPPORT:
        report_form = AddReportForm(initial={"title": title})
        sighting_form = AddSightingForm()
    elif request.user.role == User.ADMIN or request.user.role == User.MODERATOR:
        report_form = AdminReportForm(initial={"title": title})
        request_domain = get_current_site(request).domain
        report_form.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
            role_domains=Domain.objects.filter(domain=request_domain).first(),
        )
        sighting_form = AddSightingForm()

    else:
        report_form = CommunityLiaisonForm(
            initial={"title": title}
        )
        sighting_form = AddSightingForm()
    context = {"report_form": report_form, "sighting_form": sighting_form}
    return render(request, "report/add_report.html", context)



@login_required
def add_sighting(request, report_public_id):
    matched_clicked_report = Report.objects.filter(public_id=report_public_id).first()
    if request.user.role == User.END_USER:
        sighting_form = EndUserSightingForm()
    else:
        sighting_form = AddSightingForm()

    context = {
        "report": matched_clicked_report,
        "report_public_id": matched_clicked_report.public_id,
        "sighting_form": sighting_form,
    }
    return render(request, "report/add_sighting.html", context)


@login_required
@require_http_methods(["POST"])
def create_report(request):
    if request.method == "POST":
        if request.user.role == User.END_USER:
            report_form = AddReportForm(request.POST)
            sighting_form = EndUserSightingForm(request.POST)
        elif request.user.role == User.SUPPORT:
            report_form = AddReportForm(request.POST)
            sighting_form = AddSightingForm(request.POST)

        elif request.user.role == User.ADMIN or request.user.role == User.MODERATOR:
            report_form = AdminReportForm(request.POST)
            sighting_form = AddSightingForm(request.POST)

        else:
            report_form = CommunityLiaisonForm(request.POST)
            sighting_form = AddSightingForm(request.POST)
        request_domain = get_current_site(request).domain
        domain_query = Domain.objects.filter(domain=request_domain)
        if domain_query.exists():
            domain = domain_query.first()
        else:
            domain = Domain.objects.all().first()
        locator = Nominatim(user_agent="wikirumours")
        report_location_data = request.POST.get("report-location", None)
        sighting_location_data = request.POST.get("sighting-location", None)
        error_message = "Please make sure to select a location."
        if not report_location_data:
            report_form.add_error('location', error_message)
        if not sighting_location_data:
            sighting_form.add_error('location', error_message)
        
        if report_form.is_valid() and sighting_form.is_valid():
            report_location = re.split(r"[()\s]", report_location_data)
            sighting_location = re.split(r"[()\s]", sighting_location_data)
            report_latlong = "{},{}".format(report_location[3], report_location[2])
            sighting_latlong = "{},{}".format(sighting_location[3], sighting_location[2])
            try:
                report_address = locator.reverse(report_latlong)
                sighting_address = locator.reverse(sighting_latlong)
            except Exception:
                report_address = report_latlong
                sighting_address = sighting_latlong

            report = report_form.save(commit=False)

            if not valid_report_resolution(report):
                report_form.add_error('resolution', "Resolution is required for the selected status")
                context = {"report_form": report_form, "sighting_form": sighting_form}
                return render(request, "report/add_report.html", context)

            report.domain = domain
            report.reported_by = request.user
            report.address = report_address

            report.save()
            report_form._save_m2m()

            sighting = sighting_form.save(commit=False)
            sighting.report = report
            sighting.user = request.user
            sighting.is_first_sighting = True
            sighting.address = sighting_address

            if not sighting.reported_via:
                reported_via_internet = ReportedViaChoice.objects.filter(name="Internet").first()
                if reported_via_internet:
                    sighting.reported_via = reported_via_internet

            sighting.save()
            new_report_alert(report)
            log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Create Report','report':report,'sighting':sighting}
            create_user_log(log_data)
            return redirect(reverse("index"))
        else:
            context = {"report_form": report_form, "sighting_form": sighting_form}
            return render(request, "report/add_report.html", context)


@login_required
def create_sighting(request, report_public_id=None):
    if request.method == "POST":
        if request.user.role == User.END_USER:
            form = EndUserSightingForm(request.POST)
        else:
            form = AddSightingForm(request.POST)
        report = Report.objects.filter(public_id=report_public_id).first()
        locator = Nominatim(user_agent="wikirumours")
        sighting_location_data = request.POST.get("sighting-location", None)
        error_message = "Please make sure to select a location."
        if not sighting_location_data:
            form.add_error('location', error_message)

        if form.is_valid():
            sighting_location = re.split(r"[()\s]", sighting_location_data)
            sighting_latlong = "{},{}".format(sighting_location[3], sighting_location[2])
            try:
                sighting_address = locator.reverse(sighting_latlong)
            except Exception:
                sighting_address = sighting_latlong
            sighting = form.save(commit=False)
            sighting.report = report
            sighting.user = request.user
            sighting.address = sighting_address

            if not sighting.reported_via:
                reported_via_internet = ReportedViaChoice.objects.filter(name="Internet").first()
                if reported_via_internet:
                    sighting.reported_via = reported_via_internet

            sighting.save()
            log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Create Sighting','report':report,'sighting':sighting}
            create_user_log(log_data)
            return redirect(reverse("index"))
        else:
            context = {
                "sighting_form": form,
                "report": report,
                "report_public_id": report.public_id,
            }
            return render(request, "report/add_sighting.html", context)


def reports_and_sightings(request, report_public_id):
    user = request.user
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    report_query = Report.objects.filter(public_id=report_public_id)
    if domain.is_root_domain:
        report_to_view = report_query.first()
    else:
        report_to_view = report_query.first()

    if report_to_view is not None:
        first_sighting_report = Sighting.objects.filter(
            report=report_to_view, is_first_sighting=True
        ).first()
        if user.is_anonymous:
            added_sightings = None

        else:
            added_sightings = Sighting.objects.filter(
                report=report_to_view, user=request.user
            ).first()

        if request.user.role == User.ADMIN or request.user.role == User.MODERATOR:
            comments = Comment.objects.filter(report=report_to_view)
        else:
            comments = Comment.objects.filter(report=report_to_view, is_hidden=False)

        all_sightings = Sighting.objects.filter(report=report_to_view)


        if not request.user.is_anonymous:
            is_report_watchlisted = WatchlistedReport.objects.filter(user=request.user, report=report_to_view).exists()
        else:
            is_report_watchlisted = False

        slider_start_date = '2010-01-01'
        slider_end_date = '2022-01-01'

        if all_sightings.count():
            slider_start_date = all_sightings.order_by('heard_on').first().heard_on
            slider_end_date = all_sightings.order_by('-heard_on').first().heard_on

            if slider_start_date:
                slider_start_date = slider_start_date - timedelta(days=2)
                slider_start_date = slider_start_date.strftime("%Y-%m-%d")
            if slider_end_date:
                slider_end_date = slider_end_date + timedelta(days=2)
                slider_end_date = slider_end_date.strftime("%Y-%m-%d")
        context = {
            "report": report_to_view,
            "is_report_watchlisted": is_report_watchlisted,
            "first_sighting_report": first_sighting_report,
            "added_sightings": added_sightings,
            "comments": comments,
            "comments_count": comments.count(),
            "all_sightings": all_sightings,
            "sightings_count": all_sightings.count(),
            "heard_by_others": all_sightings.count() - 1,
            "slider_start_date": slider_start_date,
            "slider_end_date": slider_end_date,
            "GOOGLE_MAPS_KEY": GOOGLE_MAPS_KEY,
            "location_array": json.dumps(get_location_array(all_sightings)),
        }
        return context

    else:
        return None




def view_report(request, report_public_id):
    data = reports_and_sightings(request, report_public_id)
    report_object = data.get('report')
    if data is not None:
        if request.user.is_authenticated:
            edit_permission = request.user.can_edit_report(report_object)
        else:
            edit_permission = False
        context = {'edit_permission':edit_permission}
        context.update(data)
        return render(request, "report/view_report.html", context)
    else:
        return redirect(reverse("login"))



def sightings(request, report_public_id):
    data = reports_and_sightings(request, report_public_id)
    if data is not None:
        all_sightings = data.get("all_sightings")
        paginator = Paginator(all_sightings, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
        }
        context.update(data)

        return render(request, "report/sightings.html", context)
    else:

        return redirect(reverse("login"))


def comments(request, report_public_id):
    data = reports_and_sightings(request, report_public_id)
    if data is not None:
        if request.user.is_authenticated:
            flagged_comments = [fc.comment for fc in FlaggedComment.objects.filter(flagged_by=request.user)]
        else:
            flagged_comments = []
        if request.user.is_authenticated:
            report = Report.objects.get(public_id=report_public_id)
            edit_permission = request.user.can_edit_report(report)
        else:
            edit_permission = False
        context = {
            "flagged_comments": flagged_comments,'edit_permission':edit_permission
        }
        context.update(data)
        return render(request, "report/comments.html", context)
    else:
        return redirect(reverse("login"))


def flag_comment(request, report_public_id, comment_id):
    if request.user.is_anonymous:
        return redirect(reverse("login"))
    try:
        report = Report.objects.get(public_id=report_public_id)
        comment = Comment.objects.get(id=comment_id)

        flagged_comment, created = FlaggedComment.objects.update_or_create(
            comment=comment,
            flagged_by=request.user
        )
        log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Flag Comment','report':report,'comment':comment}
        create_user_log(log_data)
        return redirect(reverse("comments", kwargs={"report_public_id": report_public_id}))

    except Report.DoesNotExist:
        return HttpResponseNotFound()
    except Comment.DoesNotExist:
        return HttpResponseNotFound()


@login_required
def hide_comment(request, comment_id):
    comment_to_hide = Comment.objects.filter(id=comment_id).first()
    comment_to_hide.is_hidden = True
    comment_to_hide.save()
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Hide Comment','report':comment_to_hide.report,'comment':comment_to_hide}
    create_user_log(log_data)
    return redirect(
        reverse("comments", kwargs={"report_public_id": comment_to_hide.report.public_id})
    )


@login_required
def show_comment(request, comment_id):
    comment_to_show = Comment.objects.filter(id=comment_id).first()
    comment_to_show.is_hidden = False
    comment_to_show.save()
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Show Comment','report':comment_to_show.report,'comment':comment_to_show}
    create_user_log(log_data)
    return redirect(
        reverse("comments", kwargs={"report_public_id": comment_to_show.report.public_id})
    )


@login_required
def my_activity(request):
    reports = Report.objects.filter(reported_by=request.user)
    sightings = Sighting.objects.filter(
        user=request.user, is_first_sighting=False
    )
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    if not domain.is_root_domain:
        reports = reports.filter(domain=domain)
        sightings = sightings.filter(report__domain=domain)
    watchlisted_reports = Report.objects.filter(watchlistedreport__user=request.user, domain=domain).order_by('-watchlistedreport__created_at')
    watchlisted_reports_paginator = Paginator(watchlisted_reports, 10)
    watchlisted_reports_page_number = request.GET.get("watchlisted_page")
    watchlisted_reports_page_obj = watchlisted_reports_paginator.get_page(watchlisted_reports_page_number)

    reports_paginator = Paginator(reports, 10)
    reports_page_number = request.GET.get("reports_page")
    reports_page_obj = reports_paginator.get_page(reports_page_number)

    sightings_paginator = Paginator(sightings, 10)
    sightings_page_number = request.GET.get("sightings_page")
    sightings_page_obj = sightings_paginator.get_page(sightings_page_number)
    context = {
        "reports_page_obj": reports_page_obj,
        "reports": reports_page_obj.object_list,
        "sightings_page_obj": sightings_page_obj,
        "sightings": sightings_page_obj.object_list,
        "watchlisted_reports_page_obj": watchlisted_reports_page_obj,
        "watchlisted_reports": watchlisted_reports_page_obj.object_list,
    }

    return render(request, "report/my_activity.html", context)


@login_required
def edit_report(request, report_public_id=None):
    user_role = request.user.role
    report = Report.objects.filter(public_id=report_public_id).first()
    sighting = Sighting.objects.filter(report=report, is_first_sighting=True).first()

    if not request.user.can_edit_report(report):
        return HttpResponseForbidden()

    if user_role == User.END_USER or user_role == User.SUPPORT:
        report_form = AddReportForm(instance=report)
        sighting_form = AddSightingForm(instance=sighting)

    elif user_role == User.ADMIN or user_role == User.MODERATOR:

        report_form = AdminReportForm(instance=report)
        # if assigned to, show current user also even if it is not a valid choice to select.
        request_domain = get_current_site(request).domain
        if report.assigned_to:
            report_form.fields["assigned_to"].queryset = User.objects.filter(
                Q(role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
                  role_domains=Domain.objects.filter(domain=request_domain).first()) |
                Q(id=report.assigned_to.id)
            )
        else:
            report_form.fields["assigned_to"].queryset = User.objects.filter(
                role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
                role_domains=Domain.objects.filter(domain=request_domain).first()
            )

        sighting_form = AddSightingForm(instance=sighting)

    else:
        report_form = CommunityLiaisonForm(instance=report)
        sighting_form = AddSightingForm(instance=sighting)
    context = {
        "report": report,
        "report_form": report_form,
        "sighting_form": sighting_form,
    }
    return render(request, "report/edit_report.html", context)


@login_required
@require_http_methods(["POST"])
def update_report(request, report_public_id=None):
    user_role = request.user.role
    report = Report.objects.filter(public_id=report_public_id).first()
    sighting = Sighting.objects.filter(
        report__public_id=report_public_id, is_first_sighting=True
    ).first()
    if not request.user.can_edit_report(report):
        return HttpResponseForbidden()

    if user_role == User.END_USER:
        report_form = AddReportForm(request.POST, instance=report)
        sighting_form = AddSightingForm(request.POST, instance=sighting)

    elif user_role == User.MODERATOR or user_role == User.ADMIN:
        report_form = AdminReportForm(request.POST, instance=report)
        sighting_form = AddSightingForm(request.POST, instance=sighting)
    else:
        # user is community liaison
        report_form = CommunityLiaisonForm(request.POST, instance=report)
        sighting_form = AddSightingForm(request.POST, instance=sighting)

    locator = Nominatim(user_agent="wikirumours")
    report_location = re.split(r"[()\s]", request.POST.get("report-location"))
    sighting_location = re.split(r"[()\s]", request.POST.get("sighting-location"))
    report_latlong = "{},{}".format(report_location[3], report_location[2])
    sighting_latlong = "{},{}".format(sighting_location[3], sighting_location[2])
    try:
        report_address = locator.reverse(report_latlong)
        sighting_address = locator.reverse(sighting_latlong)
    except Exception:
        report_address = report_latlong
        sighting_address = sighting_latlong
    if request.method == 'POST':
        # check if forms are valid or not
        if report_form.is_valid() and sighting_form.is_valid():
            report = report_form.save(commit=False)

            if not valid_report_resolution(report):
                report_form.add_error('resolution', "Resolution is required for the selected status")
                context = {"report": report, "report_form": report_form, "sighting_form": sighting_form}
                return render(request, "report/edit_report.html", context)

            report.recently_edited_by = request.user
            report.address = report_address
            report.save()
            report_form._save_m2m()
            sighting = sighting_form.save(commit=False)
            sighting.report = report
            sighting.user = request.user
            sighting.is_first_sighting = True
            sighting.address = sighting_address
            sighting.save()
            log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Update Report','report':report,'sighting':sighting}
            create_user_log(log_data)
            return redirect(reverse("view_report", kwargs={"report_public_id": report.public_id}))
        else:
            context = {"report": report, "report_form": report_form, "sighting_form": sighting_form}
            return render(request, "report/edit_report.html", context)
    else:
        context = {"report": report, "report_form": report_form, "sighting_form": sighting_form}
        context.update(csrf(request))
        return render(request, "report/edit_report.html", context)




@login_required
def report_evidence(request, report_public_id):
    report = Report.objects.get(public_id=report_public_id)
    if not request.user.can_edit_report(report):
        return HttpResponseForbidden()
    if request.method == 'GET':
        context = {"report": report}
        return render(request, "report/report_evidence.html", context=context)
    else:
        context = {"report": report}
        for uploaded_file in request.FILES.getlist('evidence_files'):
            # check if each file is valid. if valid save else add error message
            mimetype = magic.from_buffer(uploaded_file.read(), mime=True)
            if not ("image" in mimetype) and not "pdf" in mimetype:
                messages.add_message(request, messages.ERROR,
                                     f"Please upload an image or a pdf only. Invalid file - {uploaded_file}")
            else:
                # save each file for report
                evidence_file = EvidenceFile(
                    report=report,
                    uploader=request.user,
                    file=uploaded_file
                )
                evidence_file.save()
                log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Report Evidence','report':report,'evidence':evidence_file}
                create_user_log(log_data)
        return render(request, "report/report_evidence.html", context=context)


def valid_report_resolution(report):
    if report.status:
        if report.status.name.lower() == Report.UNINVESTIGATED.lower() or \
                report.status.name.lower() == Report.UNDER_INVESTIGATION.lower():
            return True
        if not report.resolution:
            return False
        return True
    return True


@login_required
def edit_sighting(request, sighting_id=None):
    sighting = Sighting.objects.filter(id=sighting_id).first()

    if not request.user.can_edit_sighting(sighting):
        return HttpResponseForbidden()

    sighting_form = AddSightingForm(instance=sighting)
    context = {"sighting": sighting, "sighting_form": sighting_form}
    return render(request, "report/edit_sighting.html", context)


@login_required
@require_http_methods(["POST"])
def update_sighting(request, sighting_id=None):
    if request.method == "POST":

        sighting = Sighting.objects.filter(id=sighting_id).first()
        sighting_form = AddSightingForm(request.POST, instance=sighting)

        if not request.user.can_edit_sighting(sighting):
            return HttpResponseForbidden()

        locator = Nominatim(user_agent="wikirumours")
        sighting_location = re.split(r"[()\s]", request.POST.get("sighting-location"))
        sighting_latlong = "{},{}".format(sighting_location[3], sighting_location[2])
        try:
            sighting_address = locator.reverse(sighting_latlong)
        except Exception:
            sighting_address = sighting_latlong

        if sighting_form.is_valid():
            sighting = sighting_form.save(commit=False)
            sighting.address = sighting_address
            sighting.save()
            log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Update Sighting','sighting':sighting,'report':sighting.report}
            create_user_log(log_data)
            return redirect(reverse("index"))
        else:
            context = {
                "sighting_form": sighting_form,
                "sighting": sighting,
            }
            return render(request, "report/edit_sighting.html", context)


@login_required
def my_task(request):
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    if not domain.is_root_domain:
        reports = request.user.get_tasks(domain)
    else:
        reports = request.user.get_tasks()

    paginator = Paginator(reports, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj, "reports": page_obj.object_list}
    return render(request, "report/my_task.html", context)


@login_required
def add_comment(request):
    report_public_id = request.POST["report_public_id"]
    comment = request.POST["comment"]
    report = Report.objects.filter(public_id=report_public_id).first()
    comment = Comment.objects.create(comment=comment, user=request.user, report=report)
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Add Comment','comment':comment,'report':report}
    create_user_log(log_data)
    return redirect(reverse("comments", kwargs={"report_public_id": report_public_id}))


@login_required
def delete_comment(request, comment_id=None):
    comment = Comment.objects.filter(id=comment_id).first()
    report = Report.objects.filter(id=comment.report.id).first()

    if not request.user.can_delete_comment(comment):
        return redirect(reverse("login"))

    comment.delete()
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Remove Comment','report':report}
    create_user_log(log_data)
    return redirect(reverse("comments", kwargs={"report_public_id": report.public_id}))


def statistics(request):
    form = ReportFilterForm(request.GET)
    return render(request, "report/statistics.html", {
        'form': form,
        "MAPBOX_API_KEY": MAPBOX_API_KEY,
    })


@api_view(('GET',))
def statistics_data(request):
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)

    # get reports matching domain and dates

    all_sightings = Sighting.objects.order_by('-heard_on')
    all_reports = Report.objects.order_by('-occurred_on')

    if not start_date and not end_date:
        pass
    else:
        all_sightings = all_sightings.filter(heard_on__gte=start_date, heard_on__lte=end_date)
        all_reports = Report.objects.filter(occurred_on__gte=start_date, occurred_on__lte=end_date)

    if not domain.is_root_domain:
        all_sightings = all_sightings.filter(report__domain=domain)
        all_reports = all_reports.filter(domain=domain)

    status = request.GET.get("status")
    if status:
        all_reports = all_reports.filter(status__name=status)
        all_sightings = all_sightings.filter(report__status__name=status)

    priority = request.GET.get("priority")
    if priority:
        all_reports = all_reports.filter(priority__name=priority)
        all_sightings = all_sightings.filter(report__priority__name=priority)

    country = request.GET.get("country")
    if country:
        all_reports = all_reports.filter(country__name=country)
        all_sightings = all_sightings.filter(country__name=country)

    diff = datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.datetime.strptime(start_date, "%Y-%m-%d")

    # if time window is less than a year, get stats per day
    if diff.days < 365:
        all_sightings_count = all_sightings.annotate(
            day=TruncDay('heard_on')).values('day').annotate(c=Count('day')).order_by('day').values('day', 'c')
        all_reports_count = all_reports.annotate(
            day=TruncDay('occurred_on')).values('day').annotate(c=Count('day')).order_by('day').values('day', 'c')

        sightings_chart_data = []
        for sighting in all_sightings_count:
            day = sighting.get('day')
            c = sighting.get('c')
            sighting_chart_data = {"x": day.strftime("%Y-%m-%d"), "y": c}
            sightings_chart_data.append(sighting_chart_data)

        reports_chart_data = []
        for report in all_reports_count:
            day = report.get('day')
            c = report.get('c')
            report_chart_data = {"x": day.strftime("%Y-%m-%d"), "y": c}
            reports_chart_data.append(report_chart_data)

    # if time window is more than a year, get stats per month
    else:
        all_sightings_count = all_sightings.annotate(
            month=TruncMonth('heard_on')).values('month').annotate(c=Count('month')).order_by('month').values('month',
                                                                                                              'c')
        all_reports_count = all_reports.annotate(
            month=TruncMonth('occurred_on')).values('month').annotate(c=Count('month')).order_by('month').values(
            'month', 'c')

        sightings_chart_data = []
        for sighting in all_sightings_count:
            month = sighting.get('month')
            c = sighting.get('c')
            sighting_chart_data = {"x": month.strftime("%Y-%m"), "y": c}
            sightings_chart_data.append(sighting_chart_data)

        reports_chart_data = []
        for report in all_reports_count:
            month = report.get('month')
            c = report.get('c')
            report_chart_data = {"x": month.strftime("%Y-%m"), "y": c}
            reports_chart_data.append(report_chart_data)

    reports_count = all_reports.count()
    sightings_count = all_sightings.count()

    statuses_data = all_reports.values('status__name', 'status__colour', 'status__sequence_number').annotate(
        count=Count('id')).order_by('status__sequence_number')
    priorities_data = all_reports.values('priority__name', 'priority__colour', 'priority__sequence_number').annotate(
        count=Count('id')).order_by('priority__sequence_number')
    tags_data = all_reports.values('tags').annotate(
        num_times=Count('tags')
    ).order_by('-num_times')[0:20]

    # get domain-wise stats if this is the root domain
    if domain.is_root_domain:
        domain_reports = Report.objects.filter()
    else:
        domain_reports = Report.objects.filter(domain=domain)

    domain_sightings = Sighting.objects.filter(report__in=domain_reports)

    if start_date and end_date:
        domain_reports = domain_reports.filter(occurred_on__gte=start_date, occurred_on__lte=end_date)
        domain_sightings = domain_sightings.filter(heard_on__gte=start_date, heard_on__lte=end_date)

    status = request.GET.get("status")
    if status:
        domain_reports = domain_reports.filter(status__name=status)
        domain_sightings = domain_sightings.filter(report__status__name=status)

    priority = request.GET.get("priority")
    if priority:
        domain_reports = domain_reports.filter(priority__name=priority)
        domain_sightings = domain_sightings.filter(report__priority__name=priority)

    country = request.GET.get("country")
    if country:
        domain_reports = domain_reports.filter(country__name=country)
        domain_sightings = domain_sightings.filter(country__name=country)

    domains_reports_data = domain_reports.values('domain__name').annotate(count=Count('domain__name')).order_by(
        'domain__name')
    domains_sightings_data = domain_sightings.values('report__domain__name').annotate(
        count=Count('report__domain__name')).order_by('report__domain__name')

    # for heatmap
    features = []
    for sighting in all_sightings:
        if sighting.location:
            feature = {"type": "Feature",
                       "properties": {
                           "id": sighting.id,
                           "mag": 1.0,
                           "time": sighting.heard_on,
                       },
                       "geometry": {
                           "type": "Point",
                           "coordinates": [
                               sighting.location.coords[0],
                               sighting.location.coords[1],
                               0.0
                           ]
                       }}
            features.append(feature)

    feature_collection = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features
    }

    computed_tags_data = {}
    # tag data
    for report in all_reports:
        tags = report.tags.all()
        for tag in tags:
            computed_tag_data = computed_tags_data.get(tag.name, None)
            filtered_tags = list(filter(lambda x: x.name != tag.name, tags))
            if 0 == len(filtered_tags):
                continue
            tags_name = [tag.name for tag in filtered_tags]
            if computed_tag_data is not None:
                computed_tag_data.append(tags_name)
                computed_tags_data[tag.name] = computed_tag_data
            else:
                computed_tags_data[tag.name] = [tags_name]

    for key in computed_tags_data.keys():
        value = computed_tags_data.get(key)

    # Create a matrix
    master_tags = list(computed_tags_data.keys())
    tags_array = []
    for master_tag in master_tags:
        tag_values = [0 for master_tag in master_tags]
        related_tags = computed_tags_data.get(master_tag)
        for related_tag in related_tags:
            for tag in related_tag:
                related_tag_index = master_tags.index(tag)
                tag_values[related_tag_index] += 1
        tags_array.append(tag_values)

    heap = []
    for first_tag_index, tag_list in enumerate(tags_array):
        for second_tag_index, related_tag_count in enumerate(tag_list):
            if related_tag_count != 0:
                heappush(heap, (related_tag_count, first_tag_index, second_tag_index))

    MAX_COMBINATIONS = 80
    top_tag_combinations = nlargest(MAX_COMBINATIONS, heap)

    unique_tags = set([])
    _ = [unique_tags.add(t[1]) for t in top_tag_combinations]
    _ = [unique_tags.add(t[2]) for t in top_tag_combinations]

    unique_tags = list(unique_tags)
    max_combination_matrix = []
    for _ in unique_tags:
        combination_array = [0 for _ in unique_tags]
        max_combination_matrix.append(combination_array)
    for top_tag_combination in top_tag_combinations:
        count = top_tag_combination[0]
        first_tag_index = top_tag_combination[1]
        second_tag_index = top_tag_combination[2]
        max_combination_matrix[unique_tags.index(first_tag_index)][unique_tags.index(second_tag_index)] = count

    dark_mode = False
    if not request.user.is_anonymous and request.user.is_dark_mode_enabled:
        dark_mode = True
    data = {
        "reports_count": reports_count,
        "sightings_count": sightings_count,
        "feature_collection": feature_collection,
        "sightings_chart_data": sightings_chart_data,
        "reports_chart_data": reports_chart_data,
        "statuses_data": statuses_data,
        "priorities_data": priorities_data,
        "tags_data": tags_data,
        "master_tags": master_tags,
        "tags_array": max_combination_matrix,
        "domains_reports_data": domains_reports_data,
        "domains_sightings_data": domains_sightings_data,
        "dark_mode": dark_mode,
    }
    return Response(status=200, data=data)



def statistics2(request, id):
    form = ReportFilterForm(request.GET)
    return render(request, "report/statistics2.html", {
        'form': form,
        'domain_id': id,
        "MAPBOX_API_KEY": MAPBOX_API_KEY,
    })

@api_view(('GET',))
def statistics_data2(request,id):
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(id=id)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)

    # get reports matching domain and dates

    all_sightings = Sighting.objects.order_by('-heard_on')
    all_reports = Report.objects.order_by('-occurred_on')

    if not start_date and not end_date:
        pass
    else:
        all_sightings = all_sightings.filter(heard_on__gte=start_date, heard_on__lte=end_date)
        all_reports = Report.objects.filter(occurred_on__gte=start_date, occurred_on__lte=end_date)

    if not domain.is_root_domain:
        all_sightings = all_sightings.filter(report__domain=domain)
        all_reports = all_reports.filter(domain=domain)

    status = request.GET.get("status")
    if status:
        all_reports = all_reports.filter(status__name=status)
        all_sightings = all_sightings.filter(report__status__name=status)

    priority = request.GET.get("priority")
    if priority:
        all_reports = all_reports.filter(priority__name=priority)
        all_sightings = all_sightings.filter(report__priority__name=priority)

    country = request.GET.get("country")
    if country:
        all_reports = all_reports.filter(country__name=country)
        all_sightings = all_sightings.filter(country__name=country)

    diff = datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.datetime.strptime(start_date, "%Y-%m-%d")

    # if time window is less than a year, get stats per day
    if diff.days < 365:
        all_sightings_count = all_sightings.annotate(
            day=TruncDay('heard_on')).values('day').annotate(c=Count('day')).order_by('day').values('day', 'c')
        all_reports_count = all_reports.annotate(
            day=TruncDay('occurred_on')).values('day').annotate(c=Count('day')).order_by('day').values('day', 'c')

        sightings_chart_data = []
        for sighting in all_sightings_count:
            day = sighting.get('day')
            c = sighting.get('c')
            sighting_chart_data = {"x": day.strftime("%Y-%m-%d"), "y": c}
            sightings_chart_data.append(sighting_chart_data)

        reports_chart_data = []
        for report in all_reports_count:
            day = report.get('day')
            c = report.get('c')
            report_chart_data = {"x": day.strftime("%Y-%m-%d"), "y": c}
            reports_chart_data.append(report_chart_data)

    # if time window is more than a year, get stats per month
    else:
        all_sightings_count = all_sightings.annotate(
            month=TruncMonth('heard_on')).values('month').annotate(c=Count('month')).order_by('month').values('month',
                                                                                                              'c')
        all_reports_count = all_reports.annotate(
            month=TruncMonth('occurred_on')).values('month').annotate(c=Count('month')).order_by('month').values(
            'month', 'c')

        sightings_chart_data = []
        for sighting in all_sightings_count:
            month = sighting.get('month')
            c = sighting.get('c')
            sighting_chart_data = {"x": month.strftime("%Y-%m"), "y": c}
            sightings_chart_data.append(sighting_chart_data)

        reports_chart_data = []
        for report in all_reports_count:
            month = report.get('month')
            c = report.get('c')
            report_chart_data = {"x": month.strftime("%Y-%m"), "y": c}
            reports_chart_data.append(report_chart_data)

    reports_count = all_reports.count()
    sightings_count = all_sightings.count()

    statuses_data = all_reports.values('status__name', 'status__colour', 'status__sequence_number').annotate(
        count=Count('id')).order_by('status__sequence_number')
    priorities_data = all_reports.values('priority__name', 'priority__colour', 'priority__sequence_number').annotate(
        count=Count('id')).order_by('priority__sequence_number')
    tags_data = all_reports.values('tags').annotate(
        num_times=Count('tags')
    ).order_by('-num_times')[0:20]

    # get domain-wise stats if this is the root domain
    if domain.is_root_domain:
        domain_reports = Report.objects.filter()
    else:
        domain_reports = Report.objects.filter(domain=domain)

    domain_sightings = Sighting.objects.filter(report__in=domain_reports)

    if start_date and end_date:
        domain_reports = domain_reports.filter(occurred_on__gte=start_date, occurred_on__lte=end_date)
        domain_sightings = domain_sightings.filter(heard_on__gte=start_date, heard_on__lte=end_date)

    status = request.GET.get("status")
    if status:
        domain_reports = domain_reports.filter(status__name=status)
        domain_sightings = domain_sightings.filter(report__status__name=status)

    priority = request.GET.get("priority")
    if priority:
        domain_reports = domain_reports.filter(priority__name=priority)
        domain_sightings = domain_sightings.filter(report__priority__name=priority)

    country = request.GET.get("country")
    if country:
        domain_reports = domain_reports.filter(country__name=country)
        domain_sightings = domain_sightings.filter(country__name=country)

    domains_reports_data = domain_reports.values('domain__name').annotate(count=Count('domain__name')).order_by(
        'domain__name')
    domains_sightings_data = domain_sightings.values('report__domain__name').annotate(
        count=Count('report__domain__name')).order_by('report__domain__name')

    # for heatmap
    features = []
    for sighting in all_sightings:
        if sighting.location:
            feature = {"type": "Feature",
                       "properties": {
                           "id": sighting.id,
                           "mag": 1.0,
                           "time": sighting.heard_on,
                       },
                       "geometry": {
                           "type": "Point",
                           "coordinates": [
                               sighting.location.coords[0],
                               sighting.location.coords[1],
                               0.0
                           ]
                       }}
            features.append(feature)

    feature_collection = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features
    }

    computed_tags_data = {}
    # tag data
    for report in all_reports:
        tags = report.tags.all()
        for tag in tags:
            computed_tag_data = computed_tags_data.get(tag.name, None)
            filtered_tags = list(filter(lambda x: x.name != tag.name, tags))
            if 0 == len(filtered_tags):
                continue
            tags_name = [tag.name for tag in filtered_tags]
            if computed_tag_data is not None:
                computed_tag_data.append(tags_name)
                computed_tags_data[tag.name] = computed_tag_data
            else:
                computed_tags_data[tag.name] = [tags_name]

    for key in computed_tags_data.keys():
        value = computed_tags_data.get(key)

    # Create a matrix
    master_tags = list(computed_tags_data.keys())
    tags_array = []
    for master_tag in master_tags:
        tag_values = [0 for master_tag in master_tags]
        related_tags = computed_tags_data.get(master_tag)
        for related_tag in related_tags:
            for tag in related_tag:
                related_tag_index = master_tags.index(tag)
                tag_values[related_tag_index] += 1
        tags_array.append(tag_values)

    heap = []
    for first_tag_index, tag_list in enumerate(tags_array):
        for second_tag_index, related_tag_count in enumerate(tag_list):
            if related_tag_count != 0:
                heappush(heap, (related_tag_count, first_tag_index, second_tag_index))

    MAX_COMBINATIONS = 80
    top_tag_combinations = nlargest(MAX_COMBINATIONS, heap)

    unique_tags = set([])
    _ = [unique_tags.add(t[1]) for t in top_tag_combinations]
    _ = [unique_tags.add(t[2]) for t in top_tag_combinations]

    unique_tags = list(unique_tags)
    max_combination_matrix = []
    for _ in unique_tags:
        combination_array = [0 for _ in unique_tags]
        max_combination_matrix.append(combination_array)
    for top_tag_combination in top_tag_combinations:
        count = top_tag_combination[0]
        first_tag_index = top_tag_combination[1]
        second_tag_index = top_tag_combination[2]
        max_combination_matrix[unique_tags.index(first_tag_index)][unique_tags.index(second_tag_index)] = count

    dark_mode = False
    if not request.user.is_anonymous and request.user.is_dark_mode_enabled:
        dark_mode = True
    data = {
        "reports_count": reports_count,
        "sightings_count": sightings_count,
        "feature_collection": feature_collection,
        "sightings_chart_data": sightings_chart_data,
        "reports_chart_data": reports_chart_data,
        "statuses_data": statuses_data,
        "priorities_data": priorities_data,
        "tags_data": tags_data,
        "master_tags": master_tags,
        "tags_array": max_combination_matrix,
        "domains_reports_data": domains_reports_data,
        "domains_sightings_data": domains_sightings_data,
        "dark_mode": dark_mode,
    }
    return Response(status=200, data=data)



@login_required
@require_http_methods(["POST"])
def add_to_watchlist(request, report_public_id):
    report = Report.objects.filter(public_id=report_public_id).first()
    _ = WatchlistedReport.objects.get_or_create(user=request.user, report=report)
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Add To Watchlist','report':report}
    create_user_log(log_data)
    return redirect(
        reverse("comments", kwargs={"report_public_id": report.public_id})
    )


@login_required
@require_http_methods(["POST"])
def remove_from_watchlist(request, report_public_id):
    report = Report.objects.filter(public_id=report_public_id).first()
    WatchlistedReport.objects.filter(user=request.user, report=report).delete()
    log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Remove From Watchlist','report':report}
    create_user_log(log_data)
    return redirect(
        reverse("comments", kwargs={"report_public_id": report.public_id})
    )


def content_page(request, content_slug):
    cms_page = get_object_or_404(CMSPage, content_slug=content_slug)
    return render(request, 'report/content_page.html', context={'cms_page': cms_page})



class GetReportViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    http_method_names = ["get","post","put","delete"]

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        try:
            user_obj = User.objects.get(id=instance.reported_by.id)
        except:
            user_obj = None
            user_data = None
        user_data = []
        final_data = []

        if user_obj.country:
            country = user_obj.country.name
        else:
            country = None
        if user_obj.first_name:
            first_name = user_obj.first_name
        else:
            first_name = None
        if user_obj.last_name:
            last_name = user_obj.last_name
        else:
            last_name = None
        if user_obj.phone_number:
            phone_number = user_obj.phone_number
        else:
            phone_number = None
        user_data = {"user_id":user_obj.id, "first_name":first_name, "last_name":last_name, "username":user_obj.username, "email":user_obj.email,"phone_number":phone_number, "country":country, "role":user_obj.role,"is_user_anonymous":user_obj.is_user_anonymous,"is_dark_mode_enabled":user_obj.is_dark_mode_enabled,"api_post_access":user_obj.api_post_access}
        context = {'request':request}
        report_serializer = self.get_serializer(instance,context=context)
        data = report_serializer.data
        final_data.append({"report_data":data, "user_data":user_data})
        return Response({"status": 1, "message": "Report Detail.", "data":final_data})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            if not user.is_verified:
                return Response({"status": 0, "message": "You have insufficient permissions!"})
            # request_domain = get_current_site(request).domain
            request_domain = request.data['domain']
            try:
                domain = Domain.objects.get(id=request_domain)
            except:
                domain = Domain.objects.get(id=1)
            latlong = None
            # report_address = None
            country_data = request.data['country'] if request.data.get('country') else None
            country_obj = Country.objects.filter(iso_code=country_data).first()

            report_address = request.data['report_address'] if request.data.get('report_address') else None
            report_location = request.data['report_location'] if request.data.get('report_location') else None
            locator = Nominatim(user_agent="wikirumours")
            if report_address:
                report_address_temp = report_address + ", " +country_obj.name
                if report_location:
                    location = request.data.get("report_location").split(",")
                    latlong = Point(float(location[1]), float(location[0]))
                else:
                    try:
                        getLoc = locator.geocode(report_address_temp)
                        latlong = Point(float(getLoc.longitude), float(getLoc.latitude))
                        if not latlong:
                            latlong = Point(float(1), float(1))
                    except:
                        latlong = Point(float(1), float(1))
                # if request.data.get("report_location"):
                # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                # report_latlong = "{},{}".format(location[0], location[1])

                # latlong = Point(float(location[1]), float(location[0]))
                # try:
                #     report_address = locator.reverse(report_latlong)

                # except Exception:

                #     report_address = report_latlong
            else:
                if request.data.get("report_location"):
                    location = request.data.get("report_location").split(",")
                    report_latlong = "{},{}".format(location[0], location[1])

                    latlong = Point(float(location[1]), float(location[0]))
                    try:
                        report_address = locator.reverse(report_latlong)

                    except Exception:

                        report_address = report_latlong

            report_country = Country.objects.filter(
                iso_code=request.data.get("country")
            ).first()
            tags = request.data['tags']
            priority_data = request.data['priority'] if request.data.get('priority') else None
            status_data = request.data['status'] if request.data.get('status') else None
            assigned_to = request.data['assigned_to'] if request.data.get('assigned_to') else None
            emergency_alert = request.data['emergency_alert'] if request.data.get('emergency_alert') else None
            try:
                priority = PriorityChoice.objects.get(name=priority_data)
            except:
                priority = None
            try:
                status = StatusChoice.objects.get(name=status_data)
            except:
                status = None
            serializer = self.get_serializer(data=request.data)

            if emergency_alert:
                emergency = True
            else:
                emergency = False
            
            if serializer.is_valid(raise_exception=True):
                report = serializer.save(
                    reported_by=user,
                    domain=domain,
                    country=report_country,
                    location=latlong,
                    address=report_address,
                    status=status,
                    priority=priority,
                    emergency_alert = emergency
                    # tags=tags,
                )
            if "reported_by" in serializer.errors:
                return Response({"status": 0, "message": "reported_by - " + serializer.errors['reported_by'][0]})
            if "country" in serializer.errors:
                return Response({"status": 0, "message": "country - " + serializer.errors['country'][0]})
            if "domain" in serializer.errors:
                return Response({"status": 0, "message": "domain - " + serializer.errors['domain'][0]})
            if "location" in serializer.errors:
                return Response({"status": 0, "message": "location - " + serializer.errors['location'][0]})
            if "address" in serializer.errors:
                return Response({"status": 0, "message": "address - " + serializer.errors['address'][0]})
            sighting_serializer = SightingSerializer(data=request.data)
            latlong_sighting = None
            # sighting_address = None

            sighting_country_data = request.data['sighting_country'] if request.data.get('sighting_country') else None
            sighting_country_obj = Country.objects.filter(iso_code=sighting_country_data).first()

            sighting_address = request.data['sighting_address'] if request.data.get('sighting_address') else None
            sighting_location = request.data['sighting_location'] if request.data.get('sighting_location') else None
            if sighting_address:
                sighting_address_temp = sighting_address + ", " +sighting_country_obj.name
                if sighting_location:
                    location = request.data.get("sighting_location").split(",")
                    latlong_sighting = Point(float(location[1]), float(location[0]))
                else:
                    try:
                        getLoc = locator.geocode(sighting_address_temp)
                        latlong_sighting = Point(float(getLoc.longitude), float(getLoc.latitude))
                        if not latlong_sighting:
                            latlong_sighting = Point(float(1), float(1))
                    except:
                        latlong_sighting = Point(float(1), float(1))
                # if request.data.get("report_location"):
                # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                # report_latlong = "{},{}".format(location[0], location[1])

                # latlong = Point(float(location[1]), float(location[0]))
                # try:
                #     report_address = locator.reverse(report_latlong)

                # except Exception:

                #     report_address = report_latlong
            else:
                if request.data.get("sighting_location"):
                    location = request.data.get("sighting_location").split(",")
                    sighting_latlong = "{},{}".format(location[0], location[1])

                    latlong_sighting = Point(float(location[1]), float(location[0]))
                    try:
                        sighting_address = locator.reverse(sighting_latlong)

                    except Exception:

                        sighting_address = sighting_latlong

            sighting_country = Country.objects.filter(
                iso_code=request.data.get("sighting_country")
            ).first()
            
            if sighting_serializer.is_valid(raise_exception=True):
                sighting_serializer.save(
                    user=user,
                    report=report,
                    is_first_sighting=True,
                    country=sighting_country,
                    location=latlong_sighting,
                    address=sighting_address,
                )
            if "report" in serializer.errors:
                return Response({"status": 0, "message": "report - " + serializer.errors['report'][0]})
            if "country" in serializer.errors:
                return Response({"status": 0, "message": "country - " + serializer.errors['country'][0]})
            if "location" in serializer.errors:
                return Response({"status": 0, "message": "location - " + serializer.errors['location'][0]})

            log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Create Report','report':report}
            create_user_log(log_data)
            headers = self.get_success_headers(sighting_serializer.data)
            data = {"report": serializer.data}
            try:
                rep_obj = Report.objects.get(id=serializer.data['id'])
                new_report_alert(rep_obj)
            except:
                rep_obj = None
            try:
                try:
                    ld = LoginDetail.objects.get(user__id=assigned_to)
                except:
                    ld = None
                status = FCMPushView('1', "Report Created",
                                        'New Report has been assigned to you from {}.'.format(user.first_name),
                                        ld.mobile_token, ld.mobile_os,ld.user, serializer.data['id'])
                print('status', status)
                try:
                    NotificationHistoryData.objects.create(email=ld.user.email, notification_from=user,
                                                            user=ld.user, notification_type='1',
                                                            text='New Report has been assigned to you from {}.'.format(user.first_name), 
                                                            title="Report Created",
                                                            mobile_token=ld.mobile_token, post=rep_obj)
                except Exception as e:
                    print("here....", e)
            except Exception as e:
                print("why....", e)
                
            if emergency_alert:
                emergency_report_alert(rep_obj)
                try:
                    try:
                        login_detail = LoginDetail.objects.filter(user__role__in=["Admin", "Moderator", "Community Liaison"],user__role_domains__in=[domain])
                    except:
                        login_detail = None
                    for ld in login_detail:
                        status = FCMPushView('5', "Emergency Report",
                                                'There is an emergency report created by {}.'.format(user.first_name),
                                                ld.mobile_token, ld.mobile_os,ld.user, serializer.data['id'])
                        print('status', status)
                        try:
                            NotificationHistoryData.objects.create(email=ld.user.email, notification_from=user,
                                                                    user=ld.user, notification_type='5',
                                                                    text='There is an emergency report created by {}.'.format(user.first_name), 
                                                                    title="Emergency Report",
                                                                    mobile_token=ld.mobile_token,post=rep_obj)
                        except Exception as e:
                            print("here....", e)
                except Exception as e:
                    print("why....", e)
            return Response({"status": 1, "message": "Report created successfully.", "data":data})
        else:
            return Response({"status": 0, "message": "Invalid access token!"})

    def update(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        # check if user is permitted to make POST requests
        if not user.is_verified:
            return Response({"status": 0, "message": "You have insufficient permissions!"})
        if user:
            if user.role == "Admin" or user.role == "Support" or user.role == "Community Liaison" or user.role == "Moderator":
                partial = kwargs.pop("partial", False)
                instance = self.get_object()
                print("nice...", instance.id)
                if instance:
                    if instance.reported_by == user or user.role == "Admin" or user.role == "Support" or user.role == "Community Liaison" or user.role == "Moderator":
                        report_country = Country.objects.filter(iso_code=request.data.get("country")).first()
                        serializer = self.get_serializer(
                            instance, data=request.data, partial=partial
                        )
                        locator = Nominatim(user_agent="wikirumours")
                        if request.data.get("report_location"):
                            location = request.data.get("report_location").split(",")
                            report_latlong = "{},{}".format(location[0], location[1])
                            latlong = Point(float(location[1]), float(location[0]))
                            try:
                                report_address = locator.reverse(report_latlong)
                            except Exception:
                                report_address = report_latlong
                            if serializer.is_valid(raise_exception=True):
                                report = serializer.save(
                                    country=report_country, location=latlong, address=report_address
                                )
                        else:
                            if serializer.is_valid(raise_exception=True):
                                report = serializer.save(country=report_country)

                        sighting = Sighting.objects.filter(
                            report=report, is_first_sighting=True
                        ).first()
                        sighting_serializer = SightingSerializer(
                            sighting, data=request.data, partial=partial
                        )
                        sighting_country = Country.objects.filter(
                            iso_code=request.data.get("sighting_country")
                        ).first()
                        if request.data.get("sighting_location"):
                            location = request.data.get("sighting_location").split(",")
                            sighting_latlong = "{},{}".format(location[0], location[1])
                            latlong_sighting = Point(float(location[1]), float(location[0]))
                            try:
                                sighting_address = locator.reverse(sighting_latlong)
                            except Exception:
                                sighting_address = sighting_latlong

                        if sighting_serializer.is_valid(raise_exception=True):
                            sighting_serializer.save(
                                country=sighting_country,
                                location=latlong_sighting,
                                address=sighting_address,
                            )
                        else:
                            if sighting_serializer.is_valid(raise_exception=True):
                                sighting_serializer.save(country=sighting_country)
                        headers = self.get_success_headers(serializer.data)
                        # data = {'report': serializer.data, 'sighting': sighting_serializer.data}
                        log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Update Report','report':report,'sighting':sighting}
                        create_user_log(log_data)
                        # return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
                        return Response({"status": 1, "message": "Report updated successfully.", "data":serializer.data})
                    else:
                        return Response({"status": 0, "message":"You don't have permission to update this report"})
                else:
                    return Response({"status": 0, "message":"Please provide valid report id"})
            else:
                return Response({"status": 0, "message":"You don't have permission to update this report"})
        else:
            return Response({"status": 0, "message": "Invalid access token!"})

    def destroy(self, request, pk=None):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            if user.role == "Admin" or user.role == "Moderator":
                try:
                    delete_report = Report.objects.get(id=pk)
                    delete_report.delete()
                    return Response({"status":1,"message":"Report deleted successfully"})
                except:
                    return Response({"status":0,"message":"provide valid report id"})
            else:
                return Response({"status":0,"message":"you have insufficient permission!"})
        else:
            return Response({"status":0,"message":"invalid access token"})


class DropdownValueViewSet(viewsets.ModelViewSet):
    # pagination_class = StandardResultPagination
    queryset = Report.objects.all()
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        overheard_at_data = OverheardAtChoice.objects.all()
        country_data = Country.objects.all()
        reported_via_data = ReportedViaChoice.objects.all()
        source_option_data = SourceChoice.objects.all()
        status_data = StatusChoice.objects.all()
        priority_data = PriorityChoice.objects.all()
        assigned_to_data = User.objects.filter(role="Admin")

        overheard_at = []
        country = []
        reported_via = []
        source_option = []
        status = []
        priority = []
        assigned_to = []

        for overheard_obj in overheard_at_data:
            overheard_at.append({"name":overheard_obj.name})

        for country_obj in country_data:
            country.append({"id":country_obj.id,"name":country_obj.name, "iso_code":country_obj.iso_code})

        for reported_obj in reported_via_data:
            reported_via.append({"id":reported_obj.id, "name":reported_obj.name})

        for source_obj in source_option_data:
            source_option.append({"name":source_obj.name})

        for status_obj in status_data:
            status.append({"id":status_obj.id,"name":status_obj.name, "sequence_number":status_obj.sequence_number,"colour":status_obj.colour})

        for priority_obj in priority_data:
            priority.append({"id":priority_obj.id,"name":priority_obj.name, "sequence_number":priority_obj.sequence_number,"colour":priority_obj.colour})
        
        for assign_obj in assigned_to_data:
            assigned_to.append({"user_id":assign_obj.id,"username":assign_obj.username})

        data = {"overheard_at":overheard_at,"country":country,"reported_via":reported_via,
            "source_option":source_option,"status":status,"priority":priority,"assigned_to":assigned_to}

        return Response({"status": 1, "message": "Dropdown data", "data":data})



# class ReportList(generics.ListAPIView):
#     pagination_class = StandardResultPagination
#     queryset = Report.objects.all()
#     serializer_class = ReportSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter,filters.OrderingFilter]
#     filterset_fields = ['status', 'priority','country','domain']
#     search_fields = ['title', 'reported_by__username', 'priority__name', 'status__name', 'resolution', 'country__name', 'address', 'occurred_on']
#     ordering_fields = ['updated_at', 'occurred_on','sighting']

#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = self.get_serializer(page, many=True)
#             data = self.get_paginated_response(serializer.data).__dict__
#             return Response({"status":1, "message":"Report Listing","data":data['data']})

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({"status":1, "message":"Report Listing","data":serializer.data})



class DomainListViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        domain_list = []

        for query in self.queryset:
            domain_list.append({"id":query.id,"name":query.name, "domain":query.domain, "is_root_domain":query.is_root_domain})

        return Response({"status": 1, "message": "Domain List", "data":domain_list})



class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    http_method_names = ['post','get','delete']

    def retrieve(self,request, pk=None):
        comment_data = []
        comment_obj = Comment.objects.filter(report__id=pk)
        for detail in comment_obj:
            comment_data.append({"comment_id":detail.id,"username":detail.user.username,"comment":detail.comment,"report_id":detail.report.id,"created_at":detail.created_at})

        return Response({"status":1,"message":"Comment Listing",'data':comment_data})

    def create(self,request):
        report_id = request.data['report_id'] if request.data.get('report_id') else None
        comment = request.data['comment'] if request.data.get('comment') else None
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            try:
                report = Report.objects.get(id=report_id)
            except:
                return Response({"status":0,"message":"Please provide valid report id"})

            new_comment = Comment.objects.create(user=user,report=report,comment=comment)

            try:
                if report.reported_by == user:
                    ld = LoginDetail.objects.filter(user=report.assigned_to)
                else:
                    if not report.assigned_to == user:
                        ld = LoginDetail.objects.filter(Q(user=report.assigned_to) | Q(user=report.reported_by))
                    else:
                        ld = LoginDetail.objects.filter(user=report.reported_by)
                print("here....", ld)
                for login_detail in ld:
                        status = FCMPushView('3', "New Comment",
                                                'There is a comment from {} for report title {}.'.format(user.first_name,report.title),
                                                login_detail.mobile_token, login_detail.mobile_os,login_detail.user,report.id)
                        print('status', status)
                        try:
                            NotificationHistoryData.objects.create(email=login_detail.user.email, notification_from=user,
                                                                    user=login_detail.user, notification_type='3',
                                                                    text='There is a comment from {} for report title {}.'.format(user.first_name,report.title),
                                                                    title="New Comment",
                                                                    mobile_token=login_detail.mobile_token,post=report)
                        except Exception as e:
                            print("here....", e)
            except Exception as e:
                print("why....", e)

            comment_data= []
            comment_data.append({"comment_id":new_comment.id,"username":new_comment.user.username,"comment":new_comment.comment,"report_id":new_comment.report.id,"created_at":new_comment.created_at})

            return Response({"status":1,"message":"Comment created", "data":comment_data})
        else:
            return Response({"status":0,"message":"invalid access token"})


    def destroy(self, request, pk=None):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            try:
                delete_comment = Comment.objects.get(id=pk)
                delete_comment.delete()
                return Response({"status":1,"message":"Comment deleted successfully"})
            except:
                return Response({"status":0,"message":"provide valid comment id"})
        else:
            return Response({"status":0,"message":"invalid access token"})


class WatchlistViewSet(viewsets.ModelViewSet):
    queryset = WatchlistedReport.objects.all()
    http_method_names = ['post', 'delete']

    def create(self,request):
        report_id = request.data['report_id'] if request.data.get('report_id') else None
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            try:
                report = Report.objects.get(id=report_id)
            except:
                return Response({"status":0,"message":"Please provide valid report id"})

            if WatchlistedReport.objects.filter(user=user,report=report).exists():
                return Response({"status":0,"message":"Report has already been added to watchlist."})
            else:
                new_watchlist = WatchlistedReport.objects.create(user=user,report=report)

            watchlist_user_data= []
            watchlist_user_data.append({"watchlist_id":new_watchlist.id,"username":new_watchlist.user.username,"report_id":new_watchlist.report.id,"created_at":new_watchlist.created_at})

            return Response({"status":1,"message":"New watchlist created", "data":watchlist_user_data})
        else:
            return Response({"status":0,"message":"invalid access token"})


    def destroy(self, request, pk=None):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            try:
                if WatchlistedReport.objects.filter(user=user,report__id=pk).exists():
                    delete_watchlist = WatchlistedReport.objects.filter(report__id=pk, user=user)
                    for watchlist in delete_watchlist:
                        watchlist.delete()
                    return Response({"status":1,"message":"Report has been successfully removed from watchlist."})
                else:
                    return Response({"status":0,"message":"Report has not been added to watchlist yet."})
            except:
                return Response({"status":0,"message":"provide valid report id"})
        else:
            return Response({"status":0,"message":"invalid access token"})


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    http_method_names = ['post','get','delete']

    def list(self,request):
        token = request.META.get("HTTP_AUTHORIZATION")
        current_site = get_current_site(request)
        user = decrypt_token(token)
        if user:
            # request_domain = get_current_site(request).domain
            request_domain = "wikirumours.org"
            
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            if not domain.is_root_domain:
                reports = user.get_tasks(domain)
                mytask_count = reports.count()
            else:
                reports = user.get_tasks()
                mytask_count = reports.count()

            user_data = []
            role_domains_data = []
            ids = []
            # for obj in user.role_domains.filter(domain=request_domain):
            for obj in user.role_domains.all():
                ids.append(obj.id)
                role_domains_data.append({"domain_id":obj.id, "domain_name":obj.name,"domain_role":user.role})
            other_domains = Domain.objects.filter(~Q(id__in=ids))
            for obj in other_domains:
                role_domains_data.append({"domain_id":obj.id, "domain_name":obj.name,"domain_role":"End User"})
            user_data.append({"user_id":user.id,"username":user.username,"first_name":user.first_name,"last_name":user.last_name,"email":user.email,"phone_number":user.phone_number,"role":user.role,"role_domains":role_domains_data,"is_user_anonymous":user.is_user_anonymous,"mytask_count":mytask_count})

            return Response({"status":1,"message":"User Profile",'data':user_data})
        else:
            return Response({"status":0,"message":"invalid access token"})

    def create(self,request):
        first_name = request.data['first_name'] if request.data.get('first_name') else None
        last_name = request.data['last_name'] if request.data.get('last_name') else None
        phone_number = request.data['phone_number'] if request.data.get('phone_number') else None
        try:
            is_user_anonymous = request.data['is_user_anonymous']
        except:
            is_user_anonymous = None
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            if first_name:
                user.first_name = first_name
                user.save()
            if last_name:
                user.last_name = last_name
                user.save()
            if phone_number:
                user.phone_number = phone_number
                user.save()
            if is_user_anonymous != None:
                if is_user_anonymous == 1:
                    user.is_user_anonymous = True
                    user.save()
                if is_user_anonymous == 0:
                    user.is_user_anonymous = False
                    user.save()
            user_data = []
            user_data.append({"user_id":user.id,"username":user.username,"first_name":user.first_name,"last_name":user.last_name,"email":user.email,"phone_number":user.phone_number,"role":user.role,"is_user_anonymous":user.is_user_anonymous})

            return Response({"status":1,"message":"Profile updated successfully.",'data':user_data})
        else:
            return Response({"status":0,"message":"invalid access token"})


class ProfileTokenViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    http_method_names = ['post']

    def create(self,request):
        try:
            new_mobile_token = request.data['new_mobile_token']
        except:
            new_mobile_token = None

        token = request.META.get("HTTP_AUTHORIZATION")
        current_site = get_current_site(request)
        user = decrypt_token(token)
        if user:
            logged_in_user = LoginDetail.objects.filter(user=user)
            if logged_in_user:
                for item in logged_in_user:
                    old_mobile_token = item.mobile_token
            if new_mobile_token:
                if logged_in_user:
                    for item in logged_in_user:
                            item.mobile_token = new_mobile_token
                            item.save()
                fcm_obj = FCMDevice.objects.filter(user=user)
                if fcm_obj:
                    for obj in fcm_obj:
                        obj.registration_id = new_mobile_token
                        obj.save()
                # update_mobile_token(user,old_mobile_token, new_mobile_token, item.mobile_os)
            # request_domain = get_current_site(request).domain
            request_domain = "wikirumours.org"
            
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            if not domain.is_root_domain:
                reports = user.get_tasks(domain)
                mytask_count = reports.count()
            else:
                reports = user.get_tasks()
                mytask_count = reports.count()

            user_data = []
            role_domains_data = []
            ids = []
            # for obj in user.role_domains.filter(domain=request_domain):
            for obj in user.role_domains.all():
                ids.append(obj.id)
                role_domains_data.append({"domain_id":obj.id, "domain_name":obj.name,"domain_role":user.role})
            other_domains = Domain.objects.filter(~Q(id__in=ids))
            for obj in other_domains:
                role_domains_data.append({"domain_id":obj.id, "domain_name":obj.name,"domain_role":"End User"})
            user_data.append({"user_id":user.id,"username":user.username,"first_name":user.first_name,"last_name":user.last_name,"email":user.email,"phone_number":user.phone_number,"role":user.role,"role_domains":role_domains_data,"is_user_anonymous":user.is_user_anonymous,"mytask_count":mytask_count,"mobile_token":new_mobile_token})

            return Response({"status":1,"message":"User Profile",'data':user_data})
        else:
            return Response({"status":0,"message":"invalid access token"})


class ReportActivityList(generics.ListAPIView):
    pagination_class = StandardResultPagination
    queryset = Report.objects.all()

    def list(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            queryset = Report.objects.filter(reported_by=user)

            # request_domain = get_current_site(request).domain
            request_domain = "Wikirumours"
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            if not domain.is_root_domain:
                queryset = reports.filter(domain=domain)


            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ReportSerializer(page, many=True)
                report_data = self.get_paginated_response(serializer.data).__dict__
                
                return Response({"status":1, "message":"Report Activity","data":report_data['data']})
            serializer = ReportSerializer(queryset, many=True)
            return Response({"status":1, "message":"Report Activity","data":serializer.data})
            
        else:
            return Response({"status": 3, "message": "Invalid access token"})




class SightActivityList(generics.ListAPIView):
    pagination_class = StandardResultPagination
    queryset = Sighting.objects.all()

    def list(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            queryset = Sighting.objects.filter(user=user, is_first_sighting=False)

            # request_domain = get_current_site(request).domain
            request_domain = "Wikirumours"
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            if not domain.is_root_domain:
                queryset = sightings.filter(report__domain=domain)


            page = self.paginate_queryset(queryset)
         
            if page is not None:
                serializer = SightingSerializer(page, many=True)
                sighting_data = self.get_paginated_response(serializer.data).__dict__
                return Response({"status":1, "message":"Sighting Activity","data":sighting_data['data']})

            serializer = SightingSerializer(queryset, many=True)
            return Response({"status":1, "message":"Sighting Activity","data":serializer.data})
            
        else:
            return Response({"status": 3, "message": "Invalid access token"})




class WatchlistActivityList(generics.ListAPIView):
    pagination_class = StandardResultPagination
    queryset = Report.objects.all()

    def list(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            # request_domain = get_current_site(request).domain
            # # request_domain = "Wikirumours"
            # domain_query = Domain.objects.filter(domain=request_domain)
            # if domain_query.exists():
            #     domain = domain_query.first()
            # else:
            #     domain = Domain.objects.all().first()

            queryset = Report.objects.filter(watchlistedreport__user=user).order_by('-watchlistedreport__created_at')

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ReportSerializer(page, many=True)
                watchlist_report_data = self.get_paginated_response(serializer.data).__dict__
                return Response({"status":1, "message":"Watchlisted Report Activity","data":watchlist_report_data['data']})

            serializer = ReportSerializer(queryset, many=True)
            return Response({"status":1, "message":"Watchlisted Report Activity","data":serializer.data})
            
        else:
            return Response({"status": 3, "message": "Invalid access token"})





class ArticleViewSet(viewsets.ModelViewSet):
    queryset = BlogPage.objects.all()
    http_method_names = ['get']

    def list(self,request):
        # request_domain = get_current_site(request).domain
        request_domain = "Wikirumours"
        current_site = get_current_site(request)
        blog_query = BlogPage.objects.filter(visible_to_domains__name__in=[request_domain])
        print("here.....", blog_query)
        article_data = []
        
        # for obj in blog_query.visible_to_domains.all():
        #     visible_to_domain_data.append({"domain_id":obj.id, "domain_name":obj.name})
        for obj in blog_query:
            visible_to_domain_data = []
            for domain in obj.visible_to_domains.all():
                print("here....", domain)
                visible_to_domain_data.append({"domain_id":domain.id, "domain_name":domain.name})
            article_data.append({"id":obj.id,"title":obj.title,"internal_title":obj.internal_title,"content_slug":obj.content_slug,"html_content":obj.html_content,"css_content":obj.css_content,"js_content":obj.js_content,"is_visible":obj.is_visible,"created_at":obj.created_at,"updated_at":obj.updated_at,"sequence_number":obj.sequence_number,"visible_to_domain_data":visible_to_domain_data})

        return Response({"status":1,"message":"Articles List",'data':article_data})

    def retrieve(self,request, pk=None):
        article_data = []
        visible_to_domain_data = []
        try:
            obj = BlogPage.objects.get(id=pk)
        except:
            return Response({"status":0,"message":"Please provide valid article id."})
        for domain in obj.visible_to_domains.all():
                visible_to_domain_data.append({"domain_id":domain.id, "domain_name":domain.name})
        article_data.append({"id":obj.id,"title":obj.title,"internal_title":obj.internal_title,"content_slug":obj.content_slug,"html_content":obj.html_content,"css_content":obj.css_content,"js_content":obj.js_content,"is_visible":obj.is_visible,"created_at":obj.created_at,"updated_at":obj.updated_at,"sequence_number":obj.sequence_number,"visible_to_domain_data":visible_to_domain_data})
        return Response({"status":1,"message":"Article Detail",'data':article_data})



class NewReportViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultPagination
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    http_method_names = ['get']

    def list(self,request):
        # request_domain = get_current_site(request).domain
        request_domain = "wikirumours.org"
        reports = Report.objects.annotate(count=Count("sighting"))
        domain_query = Domain.objects.filter(domain=request_domain)
        if domain_query.exists():
            domain = domain_query.first()
            if not domain.is_root_domain:
                reports = reports.filter(domain=domain)

        # filters
        try:
            search = request.GET.get("search")
        except:
            search = None
        if search:
            reports = reports.filter(title__icontains=search)

        try:
            status = request.GET.get("status")
        except:
            status = None
        if status:
            reports = reports.filter(status__id=status)

        try:
            priority = request.GET.get("priority")
        except:
            priority = None
        if priority:
            reports = reports.filter(priority__id=priority)

        try:
            country = request.GET.get("country")
        except:
            country = None
        if country:
            reports = reports.filter(country__id=country)

        try:
            domain = request.GET.get("domain")
        except:
            domain = None
        if domain:
            reports = reports.filter(domain__id=domain)
        # sort
        try:
            ordering = request.GET.get("ordering")
        except:
            ordering = None

        if ordering == "most_sighted":
            reports = reports.annotate(count=Count("sighting")).order_by("-count")
        elif ordering == "recently_occurred":
            reports = reports.order_by('-occurred_on')
        else:
            reports = reports.order_by('-updated_at')

        # queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).__dict__
            return Response({"status":1, "message":"Report Listing","data":data['data']})

        serializer = self.get_serializer(queryset, many=True)
        return Response({"status":1, "message":"Report Listing","data":serializer.data})



class MyTaskList(generics.ListAPIView):
    pagination_class = StandardResultPagination
    queryset = Report.objects.all()

    def list(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if user:
            request_domain = "wikirumours.org"
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            if not domain.is_root_domain:
                queryset = user.get_tasks(domain)
            else:
                queryset = user.get_tasks(domain)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ReportSerializer(page, many=True)
                report_data = self.get_paginated_response(serializer.data).__dict__
                
                return Response({"status":1, "message":"My Tasks","data":report_data['data']})

            serializer = ReportSerializer(queryset, many=True)
            return Response({"status":1, "message":"My Tasks","data":serializer.data})
            
        else:
            return Response({"status": 3, "message": "Invalid access token"})



class ReportUpdateViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    http_method_names = ['post']

    def create(self,request):
        report_id = request.data['report_id'] if request.data.get('report_id') else None
        print("here...", report_id)
        title = request.data['title'] if request.data.get('title') else None
        tags = request.data['tags'] if request.data.get('tags') else None
        country = request.data['country'] if request.data.get('country') else None
        report_location = request.data['report_location'] if request.data.get('report_location') else None
        report_address = request.data['report_address'] if request.data.get('report_address') else None
        occurred_on = request.data['occurred_on'] if request.data.get('occurred_on') else None
        assigned_to = request.data['assigned_to'] if request.data.get('assigned_to') else None
        priority = request.data['priority'] if request.data.get('priority') else None
        status = request.data['status'] if request.data.get('status') else None
        resolution = request.data['resolution'] if request.data.get('resolution') else None
        source = request.data['source'] if request.data.get('source') else None
        overheard_at = request.data['overheard_at'] if request.data.get('overheard_at') else None
        sighting_country = request.data['sighting_country'] if request.data.get('sighting_country') else None
        sighting_location = request.data['sighting_location'] if request.data.get('sighting_location') else None
        sighting_address = request.data['sighting_address'] if request.data.get('sighting_address') else None
        reported_via = request.data['reported_via'] if request.data.get('reported_via') else None
        heard_on = request.data['heard_on'] if request.data.get('heard_on') else None
        emergency_alert = request.data['emergency_alert'] if request.data.get('emergency_alert') else None

        token = request.META.get("HTTP_AUTHORIZATION")
        user = decrypt_token(token)
        if not user.is_verified:
            return Response({"status": 0, "message": "You have insufficient permissions!"})
        if user:
            try:
                report_obj = Report.objects.get(id=report_id)
                print("here....")
            except:
                print("or here....")
                return Response({"status": 0, "message": "Please provide valid report id."})
            try:
                sighting_obj = Sighting.objects.get(report__id=report_id,is_first_sighting=True)
            except Exception as e:
                sighting_obj = None
            if user.role == "Admin" or user.role == "Support" or user.role == "Community Liaison" or user.role == "Moderator":
                if report_obj.reported_by == user or user.role == "Admin" or user.role == "Support" or user.role == "Community Liaison" or user.role == "Moderator":
                    report_country = Country.objects.filter(iso_code=country).first()
                    locator = Nominatim(user_agent="wikirumours")
                    # location = report_location.split(",")
                    # report_latlong = "{},{}".format(location[0], location[1])
                    # latlong = Point(float(location[1]), float(location[0]))
                    # try:
                    #     report_address = locator.reverse(report_latlong)
                    # except Exception:
                    #     report_address = report_latlong

                    country_obj = Country.objects.filter(iso_code=country).first()
                    if report_address:
                        report_address_temp = report_address + ", " +country_obj.name
                        if report_location:
                            location = request.data.get("report_location").split(",")
                            latlong = Point(float(location[1]), float(location[0]))
                        else:
                            try:
                                getLoc = locator.geocode(report_address_temp)
                                latlong = Point(float(getLoc.latitude), float(getLoc.longitude))
                                if not latlong:
                                    latlong = Point(float(1), float(1))
                            except:
                                latlong = Point(float(1), float(1))
                        # if request.data.get("report_location"):
                        # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                        # report_latlong = "{},{}".format(location[0], location[1])

                        # latlong = Point(float(location[1]), float(location[0]))
                        # try:
                        #     report_address = locator.reverse(report_latlong)

                        # except Exception:

                        #     report_address = report_latlong
                    else:
                        if request.data.get("report_location"):
                            location = request.data.get("report_location").split(",")
                            report_latlong = "{},{}".format(location[0], location[1])

                            latlong = Point(float(location[1]), float(location[0]))
                            try:
                                report_address = locator.reverse(report_latlong)

                            except Exception:

                                report_address = report_latlong
                        
                    report_obj.title = title
                    report_obj.tags.clear()
                    report_obj.tags.add(tags)
                    report_obj.country = report_country
                    report_obj.location = latlong
                    report_obj.address = report_address
                    report_obj.occurred_on = occurred_on
                    report_obj.recently_edited_by = user

                    # if emergency_alert:
                    #     emergency = True
                    # else:
                    #     emergency = False
                    # report_obj.emergency_alert = emergency

                    if assigned_to:
                        assigned_to_obj = User.objects.get(id=assigned_to)
                        report_obj.assigned_to = assigned_to_obj
                        assigned_to = assigned_to
                    else:
                        assigned_to = None
                    if priority:
                        priority_obj = PriorityChoice.objects.get(name=priority)
                        report_obj.priority = priority_obj
                        priority = priority
                    else:
                        priority = None
                    if status:
                        status_obj = StatusChoice.objects.get(name=status)
                        report_obj.status = status_obj
                        status = status
                    else:
                        status = None
                    if resolution:
                        report_obj.resolution = resolution
                        resolution = resolution
                    else:
                        resolution = None
                    report_obj.save()

                    if sighting_obj:
                        sighting_country = Country.objects.filter(iso_code=sighting_country).first()
                        # location = sighting_location.split(",")
                        # sighting_latlong = "{},{}".format(location[0], location[1])
                        # latlong_sighting = Point(float(location[1]), float(location[0]))
                        # try:
                        #     sighting_address = locator.reverse(sighting_latlong)
                        # except Exception:
                        #     sighting_address = sighting_latlong

                        if sighting_address:
                            sighting_address_temp = sighting_address + ", " +sighting_country.name
                            if sighting_location:
                                location = request.data.get("sighting_location").split(",")
                                latlong_sighting = Point(float(location[1]), float(location[0]))
                            else:
                                try:
                                    getLoc = locator.geocode(sighting_address_temp)
                                    latlong_sighting = Point(float(getLoc.longitude), float(getLoc.latitude))
                                    if not latlong_sighting:
                                        latlong_sighting = Point(float(1), float(1))
                                except:
                                    latlong_sighting = Point(float(1), float(1))
                            # if request.data.get("report_location"):
                            # location = request.data.get("report_location").split(",") ['20.3445','72.8788']
                            # report_latlong = "{},{}".format(location[0], location[1])

                            # latlong = Point(float(location[1]), float(location[0]))
                            # try:
                            #     report_address = locator.reverse(report_latlong)

                            # except Exception:

                            #     report_address = report_latlong
                        else:
                            if request.data.get("sighting_location"):
                                location = request.data.get("sighting_location").split(",")
                                sighting_latlong = "{},{}".format(location[0], location[1])

                                latlong_sighting = Point(float(location[1]), float(location[0]))
                                try:
                                    sighting_address = locator.reverse(sighting_latlong)

                                except Exception:

                                    sighting_address = sighting_latlong
                        sighting_obj.country = sighting_country
                        sighting_obj.location = latlong_sighting
                        sighting_obj.address = sighting_address
                        sighting_obj.heard_on = heard_on

                        if source:
                            source_obj = SourceChoice.objects.get(name=source)
                            sighting_obj.source = source_obj
                            source = source
                        else:
                            source = None
                        if overheard_at:
                            overheard_obj = OverheardAtChoice.objects.get(name=overheard_at)
                            sighting_obj.overheard_at = overheard_obj
                            overheard_at = overheard_at
                        else:
                            overheard_at = None
                        if reported_via:
                            reported_obj = ReportedViaChoice.objects.get(id=reported_via)
                            sighting_obj.reported_via = reported_obj
                            reported_via = reported_via
                            reported_via_name = reported_obj.name
                        else:
                            reported_via = None
                            reported_via_name = None

                        sighting_obj.save()
                    for tg in report_obj.tags.all():
                        tags = tg.name
                    sighting_count = Sighting.objects.filter(report=report_obj).count()
                    point_value = report_obj.location
                    point_value2 = str(point_value)
                    lat_long = re.findall('\(([^)]+)', point_value2)
                    lat_long2 = str(lat_long)[1:-1]
                    lat_long3 = lat_long2.replace("'","")
                    lat_long4 = lat_long3.replace(" ",",")

                    comment_count = Comment.objects.filter(report=report_obj).count()

                    try:
                        WatchlistedReport.objects.get(report=report_obj,user=user)
                        is_watchlisted = 1
                    except:
                        is_watchlisted = 0

                    point_value = sighting_obj.location
                    point_value2 = str(point_value)
                    lat_long = re.findall('\(([^)]+)', point_value2)
                    lat_long2 = str(lat_long)[1:-1]
                    lat_long3 = lat_long2.replace("'","")
                    lat_long4 = lat_long3.replace(" ",",")

                    if request.data.get("sighting_address"):
                        first_sighting = {"id":sighting_obj.id, "source":source,"country_name":sighting_obj.country.name,"country_iso":sighting_obj.country.iso_code,"overheard_at":overheard_at,"heard_on":heard_on,"lat_long":lat_long4,"address":sighting_address,"reported_via":reported_via, "reported_via_name":reported_via_name,"is_first_sighting":sighting_obj.is_first_sighting}
                    else:
                        first_sighting = {"id":sighting_obj.id, "source":source,"country_name":sighting_obj.country.name,"country_iso":sighting_obj.country.iso_code,"overheard_at":overheard_at,"heard_on":heard_on,"lat_long":lat_long4,"address":sighting_address.raw['display_name'],"reported_via":reported_via, "reported_via_name":reported_via_name,"is_first_sighting":sighting_obj.is_first_sighting}
                    
                    if request.data.get("report_address"):
                        data = {"report": {"id":report_obj.id,"title":report_obj.title,"tags":tags,"country":report_obj.country.iso_code,"occurred_on":report_obj.occurred_on,"address":report_address,"assigned_to":assigned_to,"sighting_count":sighting_count,"first_sighting":first_sighting,"resolution":resolution,"status":status,"priority":priority,"domain":report_obj.domain.id,"country_name":report_obj.country.name,"lat_long":lat_long4,"comment_count":comment_count,"is_watchlisted":is_watchlisted}}
                    else:
                        data = {"report": {"id":report_obj.id,"title":report_obj.title,"tags":tags,"country":report_obj.country.iso_code,"occurred_on":report_obj.occurred_on,"address":report_address.raw['display_name'],"assigned_to":assigned_to,"sighting_count":sighting_count,"first_sighting":first_sighting,"resolution":resolution,"status":status,"priority":priority,"domain":report_obj.domain.id,"country_name":report_obj.country.name,"lat_long":lat_long4,"comment_count":comment_count,"is_watchlisted":is_watchlisted}}
                    log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Update Report','report':report_obj,'sighting':sighting_obj}
                    create_user_log(log_data)
                    try:
                        watch_obj = WatchlistedReport.objects.get(report__id=report_id,user=report_obj.reported_by)
                    except:
                        watch_obj = None
                    try:
                        try:
                            if not watch_obj:
                                if report_obj.assigned_to == user:
                                    login_detail = LoginDetail.objects.filter(user=report_obj.reported_by)
                                elif report_obj.reported_by == user:
                                    login_detail = LoginDetail.objects.filter(user__id=assigned_to)
                                else:
                                    login_detail = None
                            else:
                                login_detail = None
                        except:
                            login_detail = None
                        for ld in login_detail:
                            status = FCMPushView('2', "Report Updated",
                                                    'Report of title {} has been updated by {}.'.format(title,user.first_name),
                                                    ld.mobile_token, ld.mobile_os,ld.user,report_obj.id)
                            print('status', status)
                            try:
                                NotificationHistoryData.objects.create(email=ld.user.email, notification_from=user,
                                                                        user=ld.user, notification_type='2',
                                                                        text='Report of title {} has been updated by {}.'.format(report_obj.title,user.first_name), 
                                                                        title="Report Updated",
                                                                        mobile_token=ld.mobile_token,post=report_obj)
                            except Exception as e:
                                print("here....", e)
                    except Exception as e:
                        print("why....", e)

                    try:
                        users_list = []
                        watch_obj = WatchlistedReport.objects.filter(report__id=report_id)
                        for obj in watch_obj:
                            if obj.user == user:
                                pass
                            users_list.append(obj.user.id)
                        print("here......",users_list)
                        try:
                            login_detail = LoginDetail.objects.filter(user__id__in=users_list)
                        except:
                            login_detail = None
                        for ld in login_detail:
                            status = FCMPushView('4', "Report Updated",
                                                    'Report which has been in your watchlist of title {} has been updated by {}.'.format(title,user.first_name),
                                                    ld.mobile_token, ld.mobile_os,ld.user,report_obj.id)
                            print('status', status)
                            try:
                                NotificationHistoryData.objects.create(email=ld.user.email, notification_from=user,
                                                                        user=ld.user, notification_type='4',
                                                                        text='Report which has been in your watchlist of title {} has been updated by {}.'.format(report_obj.title,user.first_name), 
                                                                        title="Report Updated",
                                                                        mobile_token=ld.mobile_token,post=report_obj)
                            except Exception as e:
                                print("here....", e)
                    except Exception as e:
                        print("why....", e)

                    # if emergency_alert:
                    #     try:
                    #         try:
                    #             login_detail = LoginDetail.objects.filter(user__role__in=["Admin", "Moderator", "Community Liaison"],user__role_domains__in=[domain])
                    #         except:
                    #             login_detail = None
                    #         for ld in login_detail:
                    #             status = FCMPushView('7', "Emergency Report Update",
                    #                                     'There is an emergency report updated by {}.'.format(user.first_name),
                    #                                     ld.mobile_token, ld.mobile_os,ld.user, report_obj.id)
                    #             print('status', status)
                    #             try:
                    #                 NotificationHistoryData.objects.create(email=ld.user.email, notification_from=user,
                    #                                                         user=ld.user, notification_type='7',
                    #                                                         text='There is an emergency report updated by {}.'.format(user.first_name), 
                    #                                                         title="Emergency Report Update",
                    #                                                         mobile_token=ld.mobile_token,post=report_obj)
                    #             except Exception as e:
                    #                 print("here....", e)
                    #     except Exception as e:
                    #         print("why....", e)

                    return Response({"status": 1, "message": "Report updated successfully", "data":data})
                else:
                    return Response({"status": 0, "message":"You don't have permission to update this report"})
            else:
                return Response({"status": 0, "message":"You don't have permission to update this report"})
        else:
            return Response({"status": 0, "message": "Invalid access token!"})


class NotificationHistoryViewset(viewsets.ModelViewSet):
    queryset = NotificationHistoryData.objects.all()
    serializer_class = NotificationSerializer
    http_method_names = ['get']

    def list(self, request):
        current_site = get_current_site(request)
        token = request.META.get("HTTP_AUTHORIZATION")
        print(token)
        user = decrypt_token(token)
        if user:
            notifications = NotificationHistoryData.objects.filter(user=user)
            # notifications = EventHistoryData.objects.filter(user=user).exclude(notification_type='admin')
            paginator = PageNumberPagination()
            paginator.page_size = 10
            result_page = paginator.paginate_queryset(notifications, request)
            if result_page is not None:
                notification_data = []
                next = paginator.page.next_page_number() if paginator.page.has_next() else None
                previous = paginator.page.previous_page_number() if paginator.page.has_previous() else None
                # count_unread = NotificationHistoryData.objects.filter(email=email,user_read_status=False).count()
                for item in result_page:
                    # time = item.time.format(format="")
                    try:
                        try:
                            post_id = str(item.post.id)
                        except:
                            post_id = None

                        print('notification_type', item.notification_type)
                        if item.notification_type == "1":
                            action = "Report create"
                        elif item.notification_type == "2":
                            action = "Report update"
                        elif item.notification_type == "3":
                            action = "Comment on report"
                        elif item.notification_type == "4":
                            action = "Watchlist Report update"
                        elif item.notification_type == "5":
                            action = "Emergency report"
                        else:
                            action = None
                        notification_data.append(
                            {"id": item.id, "notification_type": item.notification_type, "text": item.text,
                             "time": item.time, "title": item.title,
                             "user_read_status": item.user_read_status, "action": action,
                             "notifiaction_from_user_details": {"username": item.notification_from.username,
                                                                "email": item.notification_from.email,
                                                                "first_name": item.notification_from.first_name,
                                                                "last_name": item.notification_from.last_name},
                             "user": {"user_id": item.user.username,
                                      "email": item.user.email, "first_name": item.user.first_name,
                                      "last_name": item.user.last_name},
                             "post_id": post_id
                             })
                    except:
                        if item.notification_type == "1":
                            action = "Report create"
                        elif item.notification_type == "2":
                            action = "Report update"
                        elif item.notification_type == "3":
                            action = "Comment on report"
                        elif item.notification_type == "4":
                            action = "Watchlist Report update"
                        elif item.notification_type == "5":
                            action = "Emergency report"
                        else:
                            action = None
                        
                        notification_data.append(
                            {"id": item.id, "notification_type": item.notification_type, "text": item.text,
                             "time": item.time, "title": item.title, "action": action,
                             "user_read_status": item.user_read_status,
                             "notifiaction_from_user_details": {"username": None, "email": None, "first_name": None,
                                                                "last_name": None},
                             "user": {"user_id": item.user.username,
                                      "email": item.user.email, "first_name": item.user.first_name,
                                      "last_name": item.user.last_name},
                             "post_id": None
                             })
                    item.user_read_status = True
                    item.save()
                serializer = self.serializer_class(result_page, many=True)
                return Response(
                    {"status": 1, 'data': {"data": notification_data, 'count': paginator.page.paginator.count,
                                           'next': next, 'previous': previous}})
            else:
                return Response({"status": 0, "message": "no notification found"})
        else:
            return Response({"status": 3, "message": "invalid access token"})


            

