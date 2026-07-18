from django.contrib import admin

from .models import StudentTransaction

class StudentTransactionsAdmin(admin.ModelAdmin):
    model = StudentTransaction
    list_display = ['student', 'term', 'amount', 't_type', 'label']

admin.site.register(StudentTransaction, StudentTransactionsAdmin)