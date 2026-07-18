from rest_framework import viewsets

from cis.utils import CIS_user_only
from cis.campus_gate import scope_records_by_student_campus

from ...models import StudentTransaction
from ...serializers import StudentTransactionSerializer


class StudentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentTransactionSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        queryset = StudentTransaction.objects.all()

        student_id = self.request.GET.get('student_id')
        if student_id:
            queryset = queryset.filter(student__id=student_id)

        term_id = self.request.GET.get('term_id')
        if term_id:
            queryset = queryset.filter(term__id=term_id)

        label = self.request.GET.get('label')
        if label:
            queryset = queryset.filter(label=label)

        campus = self.request.GET.get('campus', '').strip()
        return scope_records_by_student_campus(
            queryset, self.request.user, selected_campus=campus or None)
