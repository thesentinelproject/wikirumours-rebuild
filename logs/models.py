from django.db import models
from report.models  import *


class UserLogs(models.Model):
    CHOICES = (
        ('Sign In','Sign In'),
        ('Update User Profile','Update User Profile'),
        ('Password Change','Password Change'),
        ('Create Report','Create Report'),
        ('Update Report','Update Report'),
        ('Report Evidence','Report Evidence'),
        ('Create Sighting','Create Sighting'),
        ('Update Sighting','Update Sighting'),
        ('Generate API Key','Generate API Key'),
        ('Add Comment','Add Comment'),
        ('Flag Comment','Flag Comment'),
        ('Hide Comment','Hide Comment'),
        ('Show Comment','Show Comment'),
        ('Remove Comment','Remove Comment'),
        ('Add To Watchlist','Add To  Watchlist'),
        ('Remove From Watchlist','Remove From Watchlist'),
        ('Sign Out','Sign Out')
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,db_index=True)
    ip_address = models.GenericIPAddressField(null=True,blank=True)
    action = models.CharField(max_length=50,choices=CHOICES)
    report = models.ForeignKey(Report, on_delete=models.CASCADE,null=True,blank=True)
    sighting = models.ForeignKey(Sighting, on_delete=models.CASCADE,null=True,blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE,null=True,blank=True)
    evidence = models.ForeignKey(EvidenceFile, on_delete=models.CASCADE,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Log' 
        verbose_name_plural = 'User Logs'

    def __str__(self):
        return self.user.first_name+' '+self.user.last_name+' ----- '+self.action