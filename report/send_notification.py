# from push_notifications.models import APNSDevice
from fcm_django.models import FCMDevice

# def APNSPushView(notification_type,device_id,title,message,to):
#     print(notification_type,device_id,title,message,to)
#     try:
#         device = APNSDevice.objects.get(registration_id=to)
#         print("ios status!!!!!!!!!!")
#         status = device.send_message(message={"device_id":device_id,"title":title,"body":message,"notification_type":notification_type})
#         print("status of push notification!!!!!!!!!!!!!!!!!!!!!!")
#         print(status)
#         return 1
#     except:
#         return 0

def FCMPushView(notification_type,title,text,to,mobile_os,user,post_id = None):
    print(mobile_os)
    try:
        if mobile_os == "ios":
            device = FCMDevice.objects.get(registration_id=to,type=mobile_os)
            print("got entry from fcmpush")
            print("ios status!!!!!!!!!!")
            data = {
                "title": title,
                "body": text,
                "notification_type":notification_type,
                "post_id":post_id

            }
            kwargs = {
                    "content_available": True,
                    'extra_kwargs': {"priority": "high","mutable_content": True,  'notification': data },
            }
            status = device.send_message(sound='default', **kwargs)
            # status = device.send_message(sound = 'default',data=data)

            # status = device.send_message(title,text)

            print(status)
        else:
            data = {
                "title": title,
                "body": text,
                "notification_type":notification_type,
                "post_id":post_id
            }
            print("data", to)
            device = FCMDevice.objects.get(user=user,registration_id=to,type=mobile_os)
            print(device)
            print("got entry from fcmpush")
            print("android status!!!!!!!!!!")
            kwargs = {
                    "content_available": True,
                    'extra_kwargs': {"priority": "high","mutable_content": True,  'notification': data, 'data':data },
            }
            status = device.send_message(sound='default', **kwargs)
            # status = device.send_message(data={"title":title,"text":text,"notification_type":notification_type})
            # status = device.send_message(data=data)
            print(status)
        if status['success']:
            print("push sent succesfullyyy!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return 1
        return 0
    except Exception as e:
        print(e)
        return 0

def add_mobile_token(user,mobile_os,mobile_token):
    try:
        if(mobile_os=="ios"):
            if(FCMDevice.objects.filter(user=user,registration_id=mobile_token,type="ios").exists()==True):
                for item in FCMDevice.objects.filter(user=user,registration_id=mobile_token,type="ios"):
                    item.delete()
            FCMDevice.objects.create(registration_id=mobile_token,type="ios",user=user)
        elif(mobile_os=="android"):
            if(FCMDevice.objects.filter(user=user,registration_id=mobile_token,type="android").exists()==True):
                for item in FCMDevice.objects.filter(user=user,registration_id=mobile_token,type="android"):
                    item.delete()
            FCMDevice.objects.create(registration_id=mobile_token,type="android",user=user)
        return 1
    except:
        return 0

def delete_mobile_token(user,mobile_token):
    try:
        if(FCMDevice.objects.filter(user=user,registration_id=mobile_token).exists()==True):
            for item in FCMDevice.objects.filter(user=user,registration_id=mobile_token):
                item.delete()
        else:
            print("Not a valid mobile_token")
        return 1
    except:
        return 0
#
def update_mobile_token(user,old_mobile_token,mobile_token,mobile_os):
    try:
        if mobile_os=="android":
            if(FCMDevice.objects.filter(user=user,registration_id=old_mobile_token,type="android").exists()==True):
                for item in FCMDevice.objects.filter(user=user,registration_id=old_mobile_token,type="android"):
                    item.registration_id = mobile_token
                    item.save()
            else:
                print("Not a android device")
        elif mobile_os=="ios":
            if(FCMDevice.objects.filter(user=user,registration_id=old_mobile_token,type="ios").exists()==True):
                for item in FCMDevice.objects.filter(user=user,registration_id=old_mobile_token,type="ios"):
                    item.registration_id = mobile_token
                    item.save()
            else:
                print("Not a ios device")
        return 1
    except:
        return 0
