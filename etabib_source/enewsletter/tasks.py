from celery import shared_task

from enewsletter.models import Newsletter


@shared_task(name='enewsletter.tasks.submit_queue')
def submit_queue():
    Newsletter.submit_queue()