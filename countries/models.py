from django.db import models


# Create your models here.
class Country(models.Model):
    name = models.CharField(max_length=255)
    iso_code = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

