from rest_framework import serializers

class TaskSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)  # tasks may have string or numeric ids
    title = serializers.CharField()
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField(required=False, default=1.0)
    importance = serializers.IntegerField(required=False, default=5)
    dependencies = serializers.ListField(child=serializers.CharField(), required=False, default=list)
