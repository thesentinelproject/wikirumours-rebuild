from .models import Report, Domain, NotificationHistoryData
from users.models import User
from newapi.models import LoginDetail
import datetime
from .send_notification import FCMPushView, add_mobile_token, delete_mobile_token, update_mobile_token
from newapi.models import LoginDetail

def InactiveAlert():
    domain = Domain.objects.get(id=1)
    print("cron running......")
    print(datetime.datetime.today())
    report_obj = Report.objects.all()
    overdue_report_count = 0
    for obj in report_obj:
        if obj.updated_at and obj.priority and obj.priority.number_of_days_before_alert:
            report_bool =  (datetime.datetime.now().replace(tzinfo=None) - obj.updated_at.replace(
                tzinfo=None)).days > obj.priority.number_of_days_before_alert
            print("ohhh.....",report_bool)
            if report_bool:
                overdue_report_count += 1
                # try:
                #     user_role = ["Admin","Support","Community Liaison","Moderator"]
                #     try:
                #         login_detail = LoginDetail.objects.filter(user__role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN],user__role_domains__in=[domain])
                #     except:
                #         login_detail = None
                #     for ld in login_detail:
                #         status = FCMPushView('6', "Inactive Report Alert",
                #                                 'You have one overdue report of title {} which you can find in My Tasks section of the site.'.format(obj.title),
                #                                 ld.mobile_token, ld.mobile_os,ld.user, obj.id)
                #         print('status', status)
                #         try:
                #             NotificationHistoryData.objects.create(email=ld.user.email, notification_from=None,
                #                                                     user=ld.user, notification_type='6',
                #                                                     text='You have one overdue report of title {} which you can find in My Tasks section of the site.'.format(obj.title), 
                #                                                     title="Inactive Report Alert",
                #                                                     mobile_token=ld.mobile_token,post=obj)
                #         except Exception as e:
                #             print("here....", e)
                # except Exception as e:
                #     print("why....", e)
            else:
                report_bool = False

    try:
        if not overdue_report_count == 0:
            user_role = ["Admin","Support","Community Liaison","Moderator"]
            try:
                login_detail = LoginDetail.objects.filter(user__role__in=["Admin", "Moderator", "Community Liaison"],user__role_domains__in=[domain])
            except:
                login_detail = None
            for ld in login_detail:
                status = FCMPushView('6', "Inactive Report Alert",
                                        'You have {} overdue reports which you can find in My Tasks section of the site.'.format(overdue_report_count),
                                        ld.mobile_token, ld.mobile_os,ld.user, obj.id)
                print('status', status)
                try:
                    NotificationHistoryData.objects.create(email=ld.user.email, notification_from=None,
                                                            user=ld.user, notification_type='6',
                                                            text='You have {} overdue reports which you can find in My Tasks section of the site.'.format(overdue_report_count),
                                                            title="Inactive Report Alert",
                                                            mobile_token=ld.mobile_token,post=obj)
                except Exception as e:
                    print("here....", e)
    except Exception as e:
        print("why....", e)

        

        
        