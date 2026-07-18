from django.contrib.auth import get_user_model
from rest_framework import serializers

from cis.models.student import Student
from cis.models.highschool import HighSchool
from cis.models.term import Term

from .models import StudentTransaction


class SlimUserSerializer(serializers.ModelSerializer):
    """Minimal user fields needed for transaction list display."""

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'psid']


class SlimHighSchoolSerializer(serializers.ModelSerializer):
    """Minimal high school fields needed for transaction list display."""

    class Meta:
        model = HighSchool
        fields = ['id', 'name']


class SlimTermSerializer(serializers.ModelSerializer):
    """Minimal term fields needed for transaction list display."""

    class Meta:
        model = Term
        fields = ['id', 'label']


class SlimStudentSerializer(serializers.ModelSerializer):
    """Minimal student fields needed for transaction list display."""
    user = SlimUserSerializer()
    highschool = SlimHighSchoolSerializer()

    class Meta:
        model = Student
        fields = ['id', 'user', 'highschool']


class StudentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for transaction list with minimal nested data."""
    student = SlimStudentSerializer()
    term = SlimTermSerializer()
    created_on = serializers.DateTimeField(format='%Y-%m-%d %I:%M %p')

    # Computed properties
    ce_url = serializers.CharField(read_only=True)
    sexy_label = serializers.CharField(read_only=True)
    format_amount = serializers.CharField(read_only=True)
    sexy_description = serializers.CharField(read_only=True)

    class Meta:
        model = StudentTransaction
        fields = [
            'id',
            'student',
            'term',
            't_type',
            'amount',
            'label',
            'description',
            'created_on',
            'ce_url',
            'sexy_label',
            'format_amount',
            'sexy_description',
        ]

        datatables_always_serialize = [
            'id',
            'student',
            'term',
            't_type',
            'amount',
            'sexy_label',
            'format_amount',
            'ce_url',
        ]
