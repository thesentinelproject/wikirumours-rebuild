from rest_framework.serializers import ModelSerializer

from users.models import User


class UserReadSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username"
        ]
        read_only_fields = ["first_name", "last_name", "username"]
        depth = 0
