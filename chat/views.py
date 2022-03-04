import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from chat.models import ChatMessage

User = get_user_model()

@login_required()
def chat(request, username=None):
    request.user.chat_messages_viewed_at = datetime.datetime.now()
    request.user.save()
    selected_user = None

    if username:
        selected_user = get_object_or_404(User, username=username)

    chats = []
    added_chat_users_set = set([])
    all_chat_messages = ChatMessage.objects.filter(Q(from_user=request.user) | Q(to_user=request.user)).order_by('-created_at')
    for message in all_chat_messages:
        if message.from_user == request.user:
            if message.to_user not in added_chat_users_set:
                chats.append({'user': message.to_user, 'message': message})
                added_chat_users_set.add(message.to_user)
        else:
            if message.from_user not in added_chat_users_set:
                chats.append({'user': message.from_user, 'message': message})
                added_chat_users_set.add(message.from_user)


    chat_messages = []
    if selected_user:
        chat_messages = ChatMessage.objects.filter(
            Q(from_user=request.user, to_user=selected_user) |
            Q(to_user=request.user, from_user=selected_user)
        ).order_by('created_at')

    context = {
        'chats': chats,
        'chat_messages': chat_messages,
        'selected_user': selected_user,
    }
    return render(request, 'chat/chat.html', context)


@login_required()
@require_http_methods(["POST"])
def send_chat_message(request, username=None):
    if username:
        selected_user = get_object_or_404(User, username=username)

    chat_message = ChatMessage(from_user=request.user, to_user=selected_user, text=request.POST.get('message_text', ''))
    chat_message.save()
    return redirect(reverse('chat', kwargs={'username': selected_user.username}))
