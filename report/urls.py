from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("new_report", views.new_report, name="new_report"),
    path("add_report", views.add_report, name="add_report"),
    path("add_sighting/<report_public_id>", views.add_sighting, name="add_sighting"),
    path("check_report", views.check_report_presence, name="check_report_presence"),
    path("create_report", views.create_report, name="create_report"),
    path("create_sighting/<report_public_id>", views.create_sighting, name="create_sighting"),
    path("view_report/<report_public_id>", views.view_report, name="view_report"),
    path("add_to_watchlist/<report_public_id>", views.add_to_watchlist, name="add_to_watchlist"),
    path("remove_from_watchlist/<report_public_id>", views.remove_from_watchlist, name="remove_from_watchlist"),
    path("hide_comment/<comment_id>", views.hide_comment, name="hide_comment"),
    path("show_comment/<comment_id>", views.show_comment, name="show_comment"),
    path("edit_report/<report_public_id>", views.edit_report, name="edit_report"),
    path("update_report/<report_public_id>", views.update_report, name="update_report"),
    path("report_evidence/<report_public_id>", views.report_evidence, name="report_evidence"),
    path("edit_sighting/<sighting_id>", views.edit_sighting, name="edit_sighting"),
    path(
        "update_sighting/<sighting_id>", views.update_sighting, name="update_sighting"
    ),
    path("my-activity", views.my_activity, name="my-activity"),
    path("my-task", views.my_task, name="my-task"),
    path("add_comment", views.add_comment, name="add_comment"),
    path("delete_comment/<comment_id>", views.delete_comment, name="delete_comment"),
    path("view_report/<report_public_id>/comments/", views.comments, name="comments"),
    path("view_report/<report_public_id>/comments/<comment_id>/flag/", views.flag_comment, name="flag_comment"),
    path("view_report/<report_public_id>/sightings/", views.sightings, name="sightings"),
    path("statistics/data", views.statistics_data, name="statistics_data"),
    path("statistics/", views.statistics, name="statistics"),

]
