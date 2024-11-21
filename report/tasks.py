import csv
import datetime
import os
from users.emails import overdue_reports_reminder
from users.models import User
from wikirumours.celery import app



@app.task(bind=True, reject_on_worker_lost=True, autoretry_for=(Exception,), retry_backoff=5, retry_jitter=True,retry_kwargs={'max_retries': 5})
def send_overdue_email_alerts(self):
    try:
        for user in User.objects.filter(role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN]):
            if user.enable_email_reminders:
                overdue_tasks = user.get_overdue_tasks()
                if overdue_tasks.count() and user.email:
                    overdue_reports_reminder(overdue_tasks, user)
    except:
        self.retry()