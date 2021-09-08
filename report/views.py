import datetime
import heapq
import json
import re
from datetime import timedelta
from heapq import heappush, nlargest
from itertools import combinations

from actstream import action
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
from users.emails import new_report_alert
from users.models import User
from wikirumours.base_settings import GOOGLE_MAPS_KEY, MAPBOX_API_KEY
from .forms import (
    AddReportForm,
    EndUserSightingForm,
    AdminReportForm,
    CommunityLiaisonForm,
    AddSightingForm, ReportFilterForm,
)
from .models import Report, Domain, Sighting, Comment, FlaggedComment, WatchlistedReport, CMSPage, ReportedViaChoice, \
    EvidenceFile
from .serializers import ReportSerializer, SightingSerializer
from .utils import get_tags_from_title, get_location_array


# Create your views here.
def index(request):
    domain = Domain.objects.filter(domain=request.get_host()).first()
    reports = Report.objects.filter(domain=domain).annotate(count=Count("sighting"))

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
        reports = reports.filter(domain=domain).annotate(count=Count("sighting")).order_by("-count")
    elif sort_by == "recently_occurred":
        reports = reports.filter(domain=domain).order_by('-occurred_on')
    else:
        reports = reports.filter(domain=domain).order_by('-updated_at')

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
    page_size = 5
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

        domain = Domain.objects.filter(domain=request.get_host()).first()
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

        headers = self.get_success_headers(sighting_serializer.data)
        data = {"report": serializer.data}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        domain = Domain.objects.filter(domain=request.get_host()).first()
        queryset = Report.objects.filter(domain=domain)
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
    authentication_classes = (
        SessionAuthentication,
        ApiAuthentication,
    )
    queryset = Sighting.objects.all()
    serializer_class = SightingSerializer
    http_method_names = ["post", "put"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        username = request.headers.get("username")
        api_key = request.headers.get("Api-key")

        user = User.objects.filter(username=username, api_key=api_key).first()
        # check if user is permitted to make POST requests
        if not user.api_post_access:
            return HttpResponseForbidden("You have insufficient permissions")

        report = Report.objects.filter(id=request.data.get("report")).first()
        sighting_country = Country.objects.filter(
            iso_code=request.data.get("country")
        ).first()
        serializer = self.get_serializer(data=request.data)
        latlong = None
        sighting_address = None
        locator = Nominatim(user_agent="wikirumours")
        if request.data.get("location"):
            location = request.data.get("location").split(",")
            sighting_latlong = "{},{}".format(location[0], location[1])
            latlong = Point(float(location[1]), float(location[0]))
            try:
                sighting_address = locator.reverse(sighting_latlong)
            except Exception:
                sighting_address = sighting_latlong
        if serializer.is_valid(raise_exception=True):
            serializer.save(
                user=user,
                report=report,
                is_first_sighting=False,
                location=latlong,
                address=sighting_address,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        username = request.headers.get("username")
        api_key = request.headers.get("Api-key")
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        user = User.objects.filter(username=username, api_key=api_key).first()

        # check if user is permitted to make POST requests
        if not user.api_post_access:
            return HttpResponseForbidden("You have insufficient permissions")

        if instance.user == user:

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            locator = Nominatim(user_agent="wikirumours")
            if request.data.get("location"):
                location = request.data.get("location").split(",")
                sighting_latlong = "{},{}".format(location[0], location[1])
                latlong = Point(float(location[1]), float(location[0]))
                try:
                    sighting_address = locator.reverse(sighting_latlong)
                except Exception:
                    sighting_address = sighting_latlong

                if serializer.is_valid(raise_exception=True):
                    sighting_country = Country.objects.filter(
                        iso_code=request.data.get("country")
                    ).first()
                    serializer.save(
                        country=sighting_country,
                        location=latlong,
                        address=sighting_address,
                    )
            else:
                if serializer.is_valid(raise_exception=True):
                    sighting_country = Country.objects.filter(
                        iso_code=request.data.get("country")
                    ).first()
                    serializer.save(country=sighting_country)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        else:
            return Response(
                {"You don't have permission to update this report"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@login_required
def new_report(request):
    return render(request, "report/new_report.html")


@login_required
def check_report_presence(request):
    title = request.POST["title"]

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

        domain = Domain.objects.filter(domain=request.get_host()).first()
        matching_reports = Report.objects.filter(domain=domain)
        matching_reports = matching_reports.filter(base_query)

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
                role_domains=Domain.objects.filter(domain=request.get_host()).first(),
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
        report_form.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
            role_domains=Domain.objects.filter(domain=request.get_host()).first(),
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
        domain = Domain.objects.filter(domain=request.get_host()).first()
        locator = Nominatim(user_agent="wikirumours")

        report_location_data = request.POST.get("report-location", None)
        sighting_location_data = request.POST.get("sighting-location", None)
        error_message = "Please make sure to select a location."
        if not report_location_data:
            report_form.add_error('location', error_message)
        if not report_location_data:
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
                print(reported_via_internet)
                if reported_via_internet:
                    sighting.reported_via = reported_via_internet

            sighting.save()

            action.send(
                sender=request.user,
                verb='created',
                target=report
            )

            new_report_alert(report)

            return redirect(reverse("index"))
        else:
            context = {"report_form": report_form, "sighting_form": sighting_form}
            return render(request, "report/add_report.html", context)


@login_required
def create_sighting(request, report_public_id=None):
    if request.method == "POST":
        form = AddSightingForm(request.POST)
        report = Report.objects.filter(public_id=report_public_id).first()
        locator = Nominatim(user_agent="wikirumours")
        sighting_location = re.split(r"[()\s]", request.POST.get("sighting-location"))
        sighting_latlong = "{},{}".format(sighting_location[3], sighting_location[2])
        try:
            sighting_address = locator.reverse(sighting_latlong)
        except Exception:
            sighting_address = sighting_latlong
        if form.is_valid():
            sighting = form.save(commit=False)
            sighting.report = report
            sighting.user = request.user
            sighting.address = sighting_address
            sighting.save()

            action.send(
                sender=request.user,
                verb='added sighting',
                action_object=sighting,
                target=report
            )
            # TODO
            # action for add report edit report 
            return redirect(reverse("index"))
        else:
            context = {
                "form": form,
                "report": report,
                "report_public_id": report.public_id,
            }
            return render(request, "report/add_sighting.html", context)


def reports_and_sightings(request, report_public_id):
    user = request.user
    domain = Domain.objects.filter(domain=request.get_host()).first()
    report_to_view = Report.objects.filter(public_id=report_public_id, domain=domain).first()
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
    if data is not None:
        context = {}
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
        context = {
            "flagged_comments": flagged_comments,
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

        action.send(
            sender=request.user,
            verb='flagged comment',
            action_object=comment,
            target=report
        )

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

    return redirect(
        reverse("comments", kwargs={"report_public_id": comment_to_hide.report.public_id})
    )


@login_required
def show_comment(request, comment_id):
    comment_to_show = Comment.objects.filter(id=comment_id).first()
    comment_to_show.is_hidden = False
    comment_to_show.save()

    return redirect(
        reverse("comments", kwargs={"report_public_id": comment_to_show.report.public_id})
    )


@login_required
def my_activity(request):
    domain = Domain.objects.filter(domain=request.get_host()).first()

    reports = Report.objects.filter(domain=domain, reported_by=request.user)
    sightings = Sighting.objects.filter(
        user=request.user, is_first_sighting=False, report__domain=domain
    )
    watchlisted_reports = Report.objects.filter(watchlistedreport__user=request.user, domain=domain).order_by(
        '-watchlistedreport__created_at')
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
        report_form.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],
            role_domains=Domain.objects.filter(domain=request.get_host()).first(),
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
        report=report_public_id, is_first_sighting=True
    ).first()
    domain = Domain.objects.filter(domain=request.get_host()).first()

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

    # check if forms are valid or not
    if report_form.is_valid() and sighting_form.is_valid():
        report = report_form.save(commit=False)

        if not valid_report_resolution(report):
            report_form.add_error('resolution', "Resolution is required for the selected status")
            context = {"report": report, "report_form": report_form, "sighting_form": sighting_form}
            return render(request, "report/edit_report.html", context)

        report.domain = domain
        report.reported_by = request.user
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
        action.send(
            sender=request.user,
            verb='edited',
            target=report
        )
        return redirect(reverse("view_report", kwargs={"report_public_id": report.public_id}))
    else:
        context = {"report": report, "report_form": report_form, "sighting_form": sighting_form}
        return render(request, "report/edit_report.html", context)


@login_required
def report_evidence(request, report_public_id=None):
    report = Report.objects.filter(public_id=report_public_id).first()

    if not request.user.can_edit_report(report):
        return HttpResponseForbidden()

    if request.method == 'GET':
        context = {"report": report}
        return render(request, "report/report_evidence.html", context=context)
    else:
        context = {"report": report}

        for file in request.FILES.getlist('evidence_files'):
            # save each file for report
            evidence_file = EvidenceFile(
                report=report,
                uploader=request.user,
                file=file
            )
            evidence_file.save()
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
            sighting.user = request.user
            sighting.address = sighting_address
            sighting.save()

            action.send(
                sender=request.user,
                verb='edited sighting',
                action_object=sighting,
                target=sighting.report
            )

            return redirect(reverse("index"))
        else:
            context = {
                "sighting_form": sighting_form,
                "sighting": sighting,
            }
            return render(request, "report/edit_sighting.html", context)


@login_required
def my_task(request):
    domain = Domain.objects.filter(domain=request.get_host()).first()
    reports = request.user.get_tasks(domain)
    paginator = Paginator(reports, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj, "reports": page_obj.object_list}
    return render(request, "report/my_task.html", context)


def search_report(request):
    keyword = request.POST.get("keyword")
    if keyword:
        reports = Report.objects.filter(title__icontains=keyword)
        paginator = Paginator(reports, 5)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context = {
            "page_obj": page_obj,
            "reports": page_obj.object_list,
            "keyword": keyword,
        }
        return TemplateResponse(request, "report/reports.html", context)
    else:
        return TemplateResponse(request, "report/reports.html")


@login_required
def add_comment(request):
    report_public_id = request.POST["report_public_id"]
    comment = request.POST["comment"]
    report = Report.objects.filter(public_id=report_public_id).first()
    comment = Comment.objects.create(comment=comment, user=request.user, report=report)

    action.send(
        sender=request.user,
        verb='added comment',
        action_object=comment,
        target=report
    )

    return redirect(reverse("comments", kwargs={"report_public_id": report_public_id}))


@login_required
def delete_comment(request, comment_id=None):
    comment = Comment.objects.filter(id=comment_id).first()
    report = Report.objects.filter(id=comment.report.id).first()

    if not request.user.can_delete_comment(comment):
        return redirect(reverse("login"))

    comment.delete()

    action.send(
        sender=request.user,
        verb='deleted a comment',
        target=report
    )
    return redirect(reverse("comments", kwargs={"report_public_id": report.public_id}))


def statistics(request):
    form = ReportFilterForm(request.GET)
    return render(request, "report/statistics.html", {
        'form': form,
        "MAPBOX_API_KEY": MAPBOX_API_KEY,
    })


@api_view(('GET',))
def statistics_data(request):
    domain = Domain.objects.filter(domain=request.get_host()).first()
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)

    # get reports matching domain and dates
    if not start_date and not end_date:
        all_sightings = Sighting.objects.filter(report__domain=domain).order_by('-heard_on')
        all_reports = Report.objects.filter(domain=domain).order_by('-occurred_on')
    else:
        all_sightings = Sighting.objects.filter(report__domain=domain, heard_on__gte=start_date,
                                                heard_on__lte=end_date).order_by('-heard_on')
        all_reports = Report.objects.filter(domain=domain, occurred_on__gte=start_date,
                                            occurred_on__lte=end_date).order_by('-occurred_on')

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
    return redirect(
        reverse("comments", kwargs={"report_public_id": report.public_id})
    )


@login_required
@require_http_methods(["POST"])
def remove_from_watchlist(request, report_public_id):
    report = Report.objects.filter(public_id=report_public_id).first()
    WatchlistedReport.objects.filter(user=request.user, report=report).delete()
    return redirect(
        reverse("comments", kwargs={"report_public_id": report.public_id})
    )


def content_page(request, content_slug):
    cms_page = get_object_or_404(CMSPage, content_slug=content_slug)
    return render(request, 'report/content_page.html', context={'cms_page': cms_page})
