from django.contrib import admin

from students.models import ClassEnrollment, Parent, Student, StudentParent


class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 0
    autocomplete_fields = ('parent',)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'school', 'email')
    list_filter = ('school',)
    search_fields = ('name', 'phone_number', 'email')
    autocomplete_fields = ('school',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'student_id',
        'first_name',
        'last_name',
        'gender',
        'school',
        'admission_date',
    )
    list_filter = ('school', 'gender')
    search_fields = ('student_id', 'first_name', 'last_name')
    autocomplete_fields = ('school',)
    inlines = (StudentParentInline,)


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'parent',
        'relationship',
        'is_primary',
        'is_emergency_contact',
    )
    list_filter = ('relationship', 'is_primary', 'is_emergency_contact')
    search_fields = (
        'student__first_name',
        'student__last_name',
        'parent__name',
        'parent__phone_number',
    )
    autocomplete_fields = ('student', 'parent')


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'class_level', 'stream', 'is_new_student')
    list_filter = ('term', 'is_new_student')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id')
    autocomplete_fields = ('student', 'term')
    raw_id_fields = ('class_level', 'stream')
