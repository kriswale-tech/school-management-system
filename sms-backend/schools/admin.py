from django.contrib import admin

from schools.models import AcademicYear, School, SchoolSetup, Term


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'email', 'setup_completed']
    search_fields = ['name', 'phone_number', 'email']


@admin.register(SchoolSetup)
class SchoolSetupAdmin(admin.ModelAdmin):
    list_display = ['school', 'current_step', 'progress_percentage', 'completed_at']
    list_filter = ['current_step']


class TermInline(admin.TabularInline):
    model = Term
    extra = 0
    fields = ['term', 'start_date', 'end_date', 'is_active']


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['academic_year', 'school', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'school']
    search_fields = ['academic_year', 'school__name']
    inlines = [TermInline]


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['term', 'school', 'academic_year', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'term', 'school']
    search_fields = ['school__name', 'academic_year__academic_year']
