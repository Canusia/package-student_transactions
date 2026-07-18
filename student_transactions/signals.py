from django.conf import settings

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.sites.models import Site

from django.template import Context, Template
from django.template.loader import get_template, render_to_string

from mailer import send_mail, send_html_mail

from cis.models.section import ClassSection, StudentRegistration
from cis.settings.registration_charges import registration_charges

from .models import StudentTransaction

from cis.middleware import current_request

@receiver(post_save, sender=StudentTransaction)
def added_new_transaction(sender, instance, created, **kwargs):
    student = instance.student

    # convert to 2 decimal places
    student.current_student_balance = round(student.student_balance(), 2)
    student.current_school_balance = round(student.school_balance(), 2)

    student.save()

    # is this a new transaction, and if type is a credit and the student balance is 0 and student does not need recommendations. change all 'requested' status registrations to 'registered'
    try:
        if created:
            if instance.t_type == 'credit' and student.current_student_balance <= 0 and not student.needs_recommendation(instance.term.id):
                pending_regs = StudentRegistration.objects.filter(
                    student=student,
                    status='applied'
                )
                for reg in pending_regs:
                    student.add_note(None, f'Auto-registered for {reg.class_section.course} / {reg.class_section.class_number} due to payment clearing balance.')

                    reg.status = 'registered'
                    reg.save()
    except Exception as e:
        print('Error auto-registering student:', e)
        
@receiver(post_delete, sender=StudentTransaction)
def deleted_transaction(sender, instance, **kwargs):
    student = instance.student

    # convert to 2 decimal places
    student.current_student_balance = round(student.student_balance(), 2)
    student.current_school_balance = round(student.school_balance(), 2)

    student.save()

    user = None
    if current_request():
        user = current_request().user

    student.add_note(user, f'Deleted {instance.term.code} {instance.sexy_description} of {instance.amount}')

@receiver(post_delete, sender=StudentRegistration)
def update_balance(sender, instance, **kwargs):
    registration = instance

    StudentTransaction.objects.filter(
        meta__registration=str(registration.id)
    ).delete()

@receiver(post_save, sender=StudentRegistration)
def manage_charges(sender, instance, **kwargs):
    charge_settings = registration_charges.from_db()

    if charge_settings.get('is_active', 'No') != 'Yes':
        return

    if not instance.pay_type or instance.pay_type == '':
        if charge_settings.get('hs_pay_type', 'class_highschool') == 'class_highschool':
            pay_type = instance.class_section.highschool.hs_pay_type
        else:
            pay_type = instance.student.highschool.hs_pay_type
    else:
        pay_type = instance.pay_type

    if instance.status in charge_settings.get('charge_trigger'):
        # check if charge exists
        if pay_type in ['Student Pay', 'School Partial Pay', 'student', 'school_partial']:
        
            # set pay type if it is blank
            if instance.pay_type == '':
                if pay_type in ['Student Pay']:
                    StudentRegistration.objects.filter(
                        id=instance.id
                    ).update(pay_type='student')
                    instance.pay_type = 'student'
                # else:
                #     StudentRegistration.objects.filter(
                #         id=instance.id
                #     ).update(pay_type='school_partial')

            try:
                StudentTransaction.objects.get(
                    meta__registration=str(instance.id),
                    label='class_charge'
                )
            except StudentTransaction.DoesNotExist:

                if instance.pay_type == '':
                    return

                cost = instance.class_section.student_cost - float(instance.non_student_pay_amount)

                if instance.pay_type == 'frl':
                    cost = 0

                # if instance.pay_type == 'school_partial':
                #     cost = cost - float(instance.non_student_pay_amount)

                if not StudentTransaction.objects.filter(
                    student=instance.student,
                    label='class_charge',
                    meta__registration=str(instance.id)
                ).exists():
                    transaction = StudentTransaction(
                        student=instance.student,
                        description=f"Student Tuition for {instance.class_section.course} / {instance.class_section.class_number}",
                        amount=cost,
                        term=instance.class_section.registration_term,
                        t_type='debit',
                        label='class_charge',
                        meta={
                            'registration': str(instance.id)
                        }
                    )
                    transaction.save()

                    if instance.pay_type == 'school_partial':
                        cost = float(instance.non_student_pay_amount)
                        transaction = StudentTransaction(
                            student=instance.student,
                            description=f"School Cost for {instance.class_section.course} / {instance.class_section.class_number}",
                            amount=cost,
                            term=instance.class_section.registration_term,
                            t_type='debit',
                            label='school_charge',
                            meta={
                                'registration': str(instance.id)
                            }
                        )
                        
                        transaction.save()

        if pay_type in ['School Full Pay', 'school_full']:
            # set pay type if it is blank
            # if instance.pay_type == '' :
            StudentRegistration.objects.filter(
                id=instance.id
            ).update(pay_type='school_full')
            
            instance.pay_type = 'school_full'
            try:
                charge = StudentTransaction.objects.get(
                    meta__registration=str(instance.id),
                    label='school_charge'
                )
            except StudentTransaction.DoesNotExist:
                
                cost = 0
                # Add school cost
                cost = float(instance.class_section.student_cost)

                if cost > 0 and not StudentTransaction.objects.filter(
                    student=instance.student,
                    meta__registration=str(instance.id),
                    label='school_charge'
                ).exists():
                    transaction = StudentTransaction(
                        student=instance.student,
                        description=f"School Cost for {instance.class_section.course} / {instance.class_section.class_number}",
                        amount=cost,
                        term=instance.class_section.registration_term,
                        t_type='debit',
                        label='school_charge',
                        meta={
                            'registration': str(instance.id)
                        }
                    )
                    
                    transaction.save()
    elif instance.status in charge_settings.get('charge_remove_trigger'):
        # check if remove charge
        StudentTransaction.objects.filter(
            meta__registration=str(instance.id)
        ).delete()