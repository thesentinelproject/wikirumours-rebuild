from .models import *



def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    return ip_address


def create_user_log(log_data):
    if not log_data.get('ip_address') == '':
        ip_address = log_data.get('ip_address')
    else:
        ip_address = None
    if not log_data.get('report') == '':
        report = log_data.get('report')
    else:
        report = None
    if not log_data.get('sighting') == '':
        sighting = log_data.get('sighting')
    else:
        sighting = None
    if not log_data.get('comment') == '':
        comment = log_data.get('comment')
    else:
        comment = None
    if not log_data.get('evidence') == '':
        evidence = log_data.get('evidence')
    else:
        evidence = None
    action = log_data.get('action')
    user = log_data.get('user')
    UserLogs.objects.create(user=user,ip_address=ip_address,action=action,report=report,sighting=sighting,comment=comment,evidence=evidence)
    