from wikirumours.celery import app
from django.core import management


@app.task(bind=True, reject_on_worker_lost=True, autoretry_for=(Exception,), retry_backoff=5, retry_jitter=True,retry_kwargs={'max_retries': 5})
def regular_database_backup(self):
    try:
        management.call_command('dbbackup','-q','-z')
    except:
        self.retry()