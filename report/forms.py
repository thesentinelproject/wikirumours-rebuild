from django.forms import ModelForm, TextInput, DateInput
from django import forms
from django.forms.widgets import Select, Textarea, DateTimeInput
from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext_lazy as _
from mapwidgets import GooglePointFieldWidget

from countries.models import Country
from report.models import Report, Sighting, StatusChoice, PriorityChoice


class AddReportForm(ModelForm):
    prefix = "report"
    title = forms.CharField(
        label=ugettext_lazy("Title"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )

    occurred_on = forms.DateTimeField(
        label=ugettext_lazy("Occurred on"),
        widget=DateTimeInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "YYYY/MM/DD Hrs:Min",
                "autocomplete": "off",
            }
        ),
        input_formats=[
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M'
        ]
    )

    class Meta:
        model = Report
        fields = ("title", "tags", "country", "location", "occurred_on")
        labels = {
            "country": _("Country"),
            "location": _("Location"),
        }
        widgets = {
            "location": GooglePointFieldWidget,
            "country": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                    "id": "sighting_country",
                    "name": "sighting_country",
                }
            ),
        }


class EndUserSightingForm(ModelForm):
    prefix = "sighting"
    heard_on = forms.DateTimeField(
        label=ugettext_lazy("Heard on"),
        widget=DateTimeInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "YYYY/MM/DD Hrs:Min",
                "autocomplete": "off",
            }
        ),
        input_formats=[
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M'
        ]
    )

    class Meta:
        model = Sighting

        fields = (
            "source",
            "overheard_at",
            "country",
            "location",
            "heard_on",
        )
        labels = {
            "source": _("Source"),
            "overheard_at": _("Overheard at"),
            "country": _("Country"),
            "location": _("Location"),
        }
        widgets = {
            "location": GooglePointFieldWidget,
            "country": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                    "id": "sighting_country",
                    "name": "sighting_country",
                }
            ),
            "overheard_at": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": False,
                    "placeholder": "",
                }
            ),
            "source": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": False,
                    "placeholder": "",
                }
            ),
        }


class AddSightingForm(ModelForm):
    prefix = "sighting"
    heard_on = forms.DateTimeField(
        label=ugettext_lazy("Heard on"),
        widget=DateTimeInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "YYYY/MM/DD Hrs:Min",
                "autocomplete": "off",
            }
        ),
        input_formats=[
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M'
        ]
    )

    class Meta:
        model = Sighting

        fields = (
            "source",
            "overheard_at",
            "country",
            "location",
            "reported_via",
            "heard_on",
        )
        labels = {
            "source": _("Source"),
            "overheard_at": _("Overheard at"),
            "country": _("Country"),
            "location": _("Location"),
            "reported_via": _("Reported via"),
        }
        widgets = {
            "location": GooglePointFieldWidget,
            "country": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                    "id": "sighting_country",
                    "name": "sighting_country",
                }
            ),
            "overheard_at": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": False,
                    "placeholder": "",
                }
            ),
            "reported_via": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "placeholder": "",
                }
            ),
            "source": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": False,
                    "placeholder": "",
                }
            ),
        }



class AdminReportForm(AddReportForm):
    class Meta(AddReportForm.Meta):
        fields = (
            "title",
            "tags",
            "country",
            "location",
            "occurred_on",
            "assigned_to",
            "priority",
            "status",
            "resolution",
        )
        labels = {
            "assigned_to": _("Assigned to"),
            "priority": _("Priority"),
            "status": _("Status"),
            "resolution": _("Resolution"),
        }
        widgets = {
            "location": GooglePointFieldWidget,
            "assigned_to": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": False,
                    "placeholder": "",
                }
            ),
            "priority": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "status": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "country": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "resolution": Textarea(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "cols": "40",
                    "rows": "10",
                    "placeholder": "",
                }
            ),
        }



class CommunityLiaisonForm(AdminReportForm):
    class Meta(AdminReportForm.Meta):
        fields = (
            "title",
            "tags",
            "country",
            "location",
            "occurred_on",
            "priority",
            "status",
            "resolution",

        )

        widgets = {
            "location": GooglePointFieldWidget,
            "priority": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "status": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "country": Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "required": "true",
                    "placeholder": "",
                }
            ),
            "resolution": Textarea(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",
                    "cols": "40",
                    "rows": "10",
                    "placeholder": "",
                }
            ),
        }


class ReportFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(ReportFilterForm, self).__init__(*args, **kwargs)

        self.fields['status'] = forms.ChoiceField(
            choices=[('', '--------')] + [(s.name, s.name) for s in StatusChoice.objects.all()], required=False,
            widget=Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",

                }
            ),
        )

        self.fields['priority'] = forms.ChoiceField(
            choices=[('', '----')] + [(p.name, p.name) for p in PriorityChoice.objects.all()], required=False,
            widget=Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",

                }
            ),
        )

        self.fields['country'] = forms.ChoiceField(
            choices=[('', '----')] + [(s.name, s.name) for s in Country.objects.all()], required=False,
            widget=Select(
                attrs={
                    "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control bg-white",

                }
            ),
        )
