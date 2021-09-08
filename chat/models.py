from django.db import models


class ChatMessage(models.Model):
    text = models.TextField(blank=False, null=False)
    from_user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_messages_from')
    to_user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_messages_to')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.from_user) + ' --> ' + str(self.to_user) + ' - ' + self.text

    class Meta:
        verbose_name = 'Message'
