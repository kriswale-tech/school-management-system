import csv
import io
from datetime import date

from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import HasActiveSchool, IsAdminOrStaff
from migration.models import MappingProfile, MigrationFile, MigrationJob, MigrationRow, MigrationSheet
from migration.serializers import (
    MappingWriteSerializer,
    MigrationFileSerializer,
    MigrationJobSerializer,
    MigrationRowSerializer,
    ProfileSerializer,
    ProfileWriteSerializer,
    target_fields_for,
    transform_choices,
)
from migration.services.audit import record_migration_audit
from migration.services.ingest import inspect_migration_file, release_stored_file, restage_sheet_header, store_upload
from migration.services.class_resolution import class_groups, confirm_class_value
from migration.services.reconciliation import approve_values, value_groups
from migration.services.mapping import (
    copy_profile_to_sheet,
    save_profile,
    save_sheet_mapping,
    suggest_mappings,
    unmapped_required,
)
from migration.services.templates import build_template_xlsx
from migration.services.staging import preview_summary, stage_sheet
from migration.services.student_commit import (
    begin_student_commit,
    decide_fields,
    decide_match,
    finish_without_unsaved,
    resume_student_commit,
    save_year_plan,
)
from migration.services.row_correction import apply_row_correction, attention_csv, attention_filename, correction_form
from migration.services.historical_commit import begin_historical_commit
from migration.services.opening_commit import begin_opening_commit
from migration.services.student_plan import plan_for_job
from migration.storage import get_migration_storage
from migration.targets import TEMPLATE_DOWNLOAD_FIELDS
from migration.tasks import (
    commit_historical_migration_task,
    commit_opening_migration_task,
    commit_student_migration_task,
)
from students.models import Student
from shared.views import SchoolScopedAPIView


class MigrationAdminView(SchoolScopedAPIView):
    permission_classes = [HasActiveSchool, IsAdminOrStaff]


class MigrationJobListView(MigrationAdminView):

    def get(self, request):
        jobs = MigrationJob.objects.filter(school=self.school).prefetch_related(
            'files__sheets__field_mappings__transforms',
        )
        return Response(MigrationJobSerializer(jobs, many=True).data)

    def post(self, request):
        serializer = MigrationJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(school=self.school, created_by=request.user)
        return Response(MigrationJobSerializer(job).data, status=status.HTTP_201_CREATED)


class MigrationJobDetailView(MigrationAdminView):

    def get(self, request, job_id):
        job = self._job(job_id)
        if job.status == MigrationJob.Status.COMMITTED:
            release_stored_file(job)
        return Response(MigrationJobSerializer(job).data)

    def delete(self, request, job_id):
        job = self._job(job_id)
        saved = job.status in {
            MigrationJob.Status.COMMITTING,
            MigrationJob.Status.PARTIALLY_COMMITTED,
            MigrationJob.Status.COMMITTED,
        } or MigrationRow.objects.filter(
            job=job,
            commit_status=MigrationRow.CommitStatus.COMMITTED,
        ).exists()
        if saved:
            return Response(
                {'job': 'Students from this import have been saved, so it cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _job(self, job_id):
        return get_object_or_404(
            MigrationJob.objects.filter(school=self.school).prefetch_related(
                'files__sheets__field_mappings__transforms',
            ),
            pk=job_id,
        )


class MigrationFileUploadView(MigrationJobDetailView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, job_id):
        job = self._job(job_id)
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'file': 'Choose a file to upload.'}, status=status.HTTP_400_BAD_REQUEST)
        migration_file = store_upload(
            job=job,
            uploaded_by=request.user,
            filename=upload.name,
            content=upload.read(),
            content_type=upload.content_type or '',
            role=(request.data.get('role') or '').strip(),
        )
        inspect_migration_file(str(migration_file.id))
        migration_file = MigrationFile.objects.prefetch_related(
            'sheets__field_mappings__transforms',
        ).get(pk=migration_file.id)
        return Response(
            MigrationFileSerializer(migration_file).data,
            status=status.HTTP_201_CREATED,
        )


class MigrationFileDownloadView(MigrationAdminView):

    def get(self, request, job_id, file_id):
        migration_file = get_object_or_404(
            MigrationFile.objects.select_related('job'),
            pk=file_id,
            job_id=job_id,
            job__school=self.school,
        )
        record_migration_audit(
            school=self.school,
            job=migration_file.job,
            actor=request.user,
            action='download',
            summary=f'Downloaded {migration_file.original_filename}.',
            payload={'file_id': str(migration_file.id)},
        )
        if not migration_file.storage_key:
            return Response(
                {'file': 'This import is finished, so the file has been removed.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        handle = get_migration_storage().open(migration_file.storage_key, 'rb')
        return FileResponse(
            handle,
            as_attachment=True,
            filename=migration_file.original_filename,
        )


class MigrationSheetHeaderView(MigrationAdminView):

    def post(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        header_row = request.data.get('header_row')
        try:
            header_row = int(header_row)
        except (TypeError, ValueError):
            return Response({'header_row': 'Enter the header row number.'}, status=status.HTTP_400_BAD_REQUEST)
        sheet = restage_sheet_header(sheet=sheet, header_row=header_row)
        return Response(MigrationJobSerializer(sheet.migration_file.job).data)

    def _sheet(self, job_id, sheet_id):
        return get_object_or_404(
            MigrationSheet.objects.select_related('migration_file__job'),
            pk=sheet_id,
            migration_file__job_id=job_id,
            migration_file__job__school=self.school,
        )


class MigrationSheetIncludeView(MigrationSheetHeaderView):
    def post(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        sheet.included = bool(request.data.get('included', True))
        sheet.save(update_fields=['included', 'updated_at'])
        return Response({'id': str(sheet.id), 'included': sheet.included})


class MigrationSuggestView(MigrationSheetHeaderView):
    def get(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        job = sheet.migration_file.job
        role = sheet.migration_file.role
        suggestions = suggest_mappings(sheet.detected_headers, job.job_type, job.template, role)
        return Response({
            'suggestions': suggestions,
            'targets': target_fields_for(job.job_type, job.template, role),
            'unmapped_required': unmapped_required(suggestions, job.job_type, job.template, role),
            'transforms': transform_choices(),
        })


class MigrationMappingView(MigrationSheetHeaderView):
    def put(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        serializer = MappingWriteSerializer(data=request.data.get('mappings', []), many=True)
        serializer.is_valid(raise_exception=True)
        save_sheet_mapping(sheet=sheet, mappings=serializer.validated_data)
        record_migration_audit(
            school=self.school,
            job=sheet.migration_file.job,
            actor=request.user,
            action='mapping',
            summary=f'Updated the mapping for {sheet.sheet_name}.',
        )
        job = sheet.migration_file.job
        if job.status in {MigrationJob.Status.UPLOADED, MigrationJob.Status.DRAFT}:
            job.status = MigrationJob.Status.MAPPING
            job.save(update_fields=['status', 'updated_at'])
        return Response(MigrationJobSerializer(self._job(job_id)).data)

    def _job(self, job_id):
        return get_object_or_404(
            MigrationJob.objects.filter(school=self.school).prefetch_related(
                'files__sheets__field_mappings__transforms',
            ),
            pk=job_id,
        )


class MappingProfileListView(MigrationAdminView):

    def get(self, request):
        job_type = request.query_params.get('job_type')
        profiles = MappingProfile.objects.filter(school=self.school)
        if job_type:
            profiles = profiles.filter(job_type=job_type)
        return Response(ProfileSerializer(profiles.prefetch_related('field_mappings__transforms'), many=True).data)


class MappingProfileCreateView(MigrationSheetHeaderView):
    def post(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        job = sheet.migration_file.job
        serializer = ProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = save_profile(
            school=self.school,
            user=request.user,
            name=data['name'],
            job_type=job.job_type,
            source_system=data.get('source_system') or job.source_system,
            mappings=data['mappings'],
        )
        copy_profile_to_sheet(profile=profile, sheet=sheet)
        return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


class ApplyProfileView(MigrationSheetHeaderView):
    def post(self, request, job_id, sheet_id):
        sheet = self._sheet(job_id, sheet_id)
        profile = get_object_or_404(
            MappingProfile,
            pk=request.data.get('profile_id'),
            school=self.school,
            job_type=sheet.migration_file.job.job_type,
        )
        copy_profile_to_sheet(profile=profile, sheet=sheet)
        return Response(MigrationJobSerializer(
            MigrationJob.objects.prefetch_related('files__sheets__field_mappings__transforms').get(pk=sheet.migration_file.job_id),
        ).data)


class MigrationValidateView(MigrationJobDetailView):
    def post(self, request, job_id):
        job = self._job(job_id)
        sheets = MigrationSheet.objects.filter(
            migration_file__job=job,
            included=True,
            migration_file__status=MigrationFile.Status.READY,
        )
        for sheet in sheets:
            stage_sheet(sheet)
        plan_for_job(job)
        record_migration_audit(
            school=self.school,
            job=job,
            actor=request.user,
            action='validate',
            summary='Validated staged rows.',
        )
        job.refresh_from_db()
        return Response(job.summary)


class MigrationPreviewView(MigrationJobDetailView):
    def get(self, request, job_id):
        job = self._job(job_id)
        rows = (
            MigrationRow.objects.filter(job=job, sheet__included=True)
            .select_related('sheet__migration_file')
            .order_by('sheet__sheet_name', 'source_row_number')
        )
        record_migration_audit(
            school=self.school,
            job=job,
            actor=request.user,
            action='preview',
            summary='Opened the migration preview.',
        )
        return Response({
            'summary': job.summary or preview_summary(job),
            'rows': MigrationRowSerializer(rows[:200], many=True).data,
        })


class MigrationPlanView(MigrationJobDetailView):
    page_size = 50

    def get(self, request, job_id):
        job = self._job(job_id)
        rows = MigrationRow.objects.filter(job=job, sheet__included=True).select_related('sheet')
        outcome = request.query_params.get('outcome')
        if outcome in {'saved', 'unsaved'}:
            saved_count = rows.filter(commit_status=MigrationRow.CommitStatus.COMMITTED).count()
            total_count = rows.count()
            if outcome == 'saved':
                rows = rows.filter(commit_status=MigrationRow.CommitStatus.COMMITTED)
            else:
                rows = rows.exclude(commit_status=MigrationRow.CommitStatus.COMMITTED)
            return Response(self._page(rows.order_by('source_row_number'), request, saved_count, total_count))
        attention = request.query_params.get('attention') == '1'
        if attention:
            rows = rows.exclude(validation_status=MigrationRow.ValidationStatus.READY)
        rows = rows.order_by('source_row_number')
        if request.query_params.get('all') != '1':
            rows = rows[:300]
        return Response({
            'summary': job.summary,
            'rows': MigrationRowSerializer(rows, many=True).data,
        })

    def _page(self, rows, request, saved_count, total_count):
        try:
            page_number = int(request.query_params.get('page') or 1)
        except (TypeError, ValueError):
            page_number = 1
        paginator = Paginator(rows, self.page_size)
        if paginator.count == 0:
            page_rows = []
            page_number = 1
            total_pages = 1
            start_index = 0
            end_index = 0
        else:
            page_number = min(max(page_number, 1), paginator.num_pages)
            page = paginator.page(page_number)
            page_rows = page.object_list
            total_pages = paginator.num_pages
            start_index = page.start_index()
            end_index = page.end_index()
        results = MigrationRowSerializer(page_rows, many=True).data
        return {
            'count': paginator.count,
            'page_count': len(results),
            'page': page_number,
            'page_size': self.page_size,
            'total_pages': total_pages,
            'start_index': start_index,
            'end_index': end_index,
            'has_next': page_number < total_pages and paginator.count > 0,
            'has_previous': page_number > 1 and paginator.count > 0,
            'next': None,
            'previous': None,
            'results': results,
            'saved_count': saved_count,
            'total_count': total_count,
        }


class MigrationMatchView(MigrationAdminView):
    def post(self, request, job_id, row_id):
        row = self._row(job_id, row_id)
        decision = request.data.get('decision')
        student = None
        if request.data.get('student_id'):
            student = get_object_or_404(Student, pk=request.data['student_id'], school=self.school)
        decide_match(row=row, actor=request.user, decision=decision, student=student)
        row.refresh_from_db()
        return Response(MigrationRowSerializer(row).data)

    def _row(self, job_id, row_id):
        return get_object_or_404(
            MigrationRow.objects.select_related('job', 'sheet__migration_file'),
            pk=row_id,
            job_id=job_id,
            job__school=self.school,
        )


class MigrationRowCorrectionView(MigrationMatchView):
    def get(self, request, job_id, row_id):
        return Response(correction_form(self._row(job_id, row_id)))

    def post(self, request, job_id, row_id):
        row = self._row(job_id, row_id)
        apply_row_correction(row=row, actor=request.user, values=request.data.get('values') or {})
        row.refresh_from_db()
        return Response(MigrationRowSerializer(row).data)


class MigrationAttentionReportView(MigrationJobDetailView):
    def get(self, request, job_id):
        job = self._job(job_id)
        record_migration_audit(
            school=self.school,
            job=job,
            actor=request.user,
            action='download',
            summary='Downloaded the needs-attention rows.',
        )
        response = HttpResponse(attention_csv(job), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{attention_filename(job)}"'
        return response


class MigrationFieldReviewView(MigrationMatchView):
    def post(self, request, job_id, row_id):
        row = self._row(job_id, row_id)
        decide_fields(
            row=row,
            actor=request.user,
            resolutions=request.data.get('resolutions') or {},
            guardian_decision=request.data.get('guardian_decision') or '',
        )
        row.refresh_from_db()
        return Response(MigrationRowSerializer(row).data)


class MigrationYearPlanView(MigrationJobDetailView):
    def post(self, request, job_id):
        job = self._job(job_id)
        try:
            start = date.fromisoformat(request.data.get('start_date') or '')
            end = date.fromisoformat(request.data.get('end_date') or '')
        except ValueError:
            return Response(
                {'start_date': 'Enter the historical year start and end dates.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        summary = save_year_plan(
            job=job,
            label=(request.data.get('label') or '').strip(),
            start_date=start,
            end_date=end,
        )
        return Response(summary)


class MigrationCommitView(MigrationJobDetailView):
    def post(self, request, job_id):
        if request.data.get('confirm') is not True:
            return Response(
                {'confirm': 'Confirm this import before anything is saved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job = self._job(job_id)
        if job.template == MigrationJob.Template.OPENING_BALANCES:
            job = begin_opening_commit(
                job=job,
                actor=request.user,
                confirmed_total=request.data.get('confirmed_total'),
            )
            commit_opening_migration_task.delay(str(job.id))
        elif job.template == MigrationJob.Template.HISTORICAL_FINANCE:
            job = begin_historical_commit(job=job, actor=request.user)
            commit_historical_migration_task.delay(str(job.id))
        else:
            job = begin_student_commit(job=job, actor=request.user)
            commit_student_migration_task.delay(str(job.id))
        job.refresh_from_db()
        return Response(MigrationJobSerializer(job).data)


class MigrationResumeView(MigrationJobDetailView):
    def post(self, request, job_id):
        job = self._job(job_id)
        job = resume_student_commit(job=job, actor=request.user)
        if job.template == MigrationJob.Template.OPENING_BALANCES:
            commit_opening_migration_task.delay(str(job.id))
        elif job.template == MigrationJob.Template.HISTORICAL_FINANCE:
            commit_historical_migration_task.delay(str(job.id))
        else:
            commit_student_migration_task.delay(str(job.id))
        job.refresh_from_db()
        return Response(MigrationJobSerializer(job).data)


class MigrationFinishView(MigrationJobDetailView):
    def post(self, request, job_id):
        job = finish_without_unsaved(job=self._job(job_id), actor=request.user)
        return Response(MigrationJobSerializer(job).data)


class MigrationErrorReportView(MigrationJobDetailView):
    def get(self, request, job_id):
        job = self._job(job_id)
        record_migration_audit(
            school=self.school,
            job=job,
            actor=request.user,
            action='download',
            summary='Downloaded the migration error report.',
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Sheet', 'Row', 'Student', 'Reason'])
        rows = MigrationRow.objects.filter(job=job, sheet__included=True).select_related('sheet')
        for row in rows:
            if row.commit_status in {MigrationRow.CommitStatus.COMMITTED, MigrationRow.CommitStatus.SKIPPED}:
                continue
            proposal = row.proposal or {}
            reasons = proposal.get('block_reasons') or proposal.get('reasons') or row.errors or []
            reason = '. '.join(item.get('message', '') for item in reasons if item.get('message'))
            if not reason:
                continue
            values = row.transformed_values or {}
            student = proposal.get('student_label') or f"{values.get('first_name', '')} {values.get('last_name', '')}".strip()
            writer.writerow([
                row.sheet.sheet_name,
                row.source_row_number,
                student or f'Row {row.source_row_number}',
                reason,
            ])
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="migration-errors.csv"'
        return response


class MigrationTemplateView(MigrationAdminView):
    def get(self, request, template):
        if template not in TEMPLATE_DOWNLOAD_FIELDS:
            return Response(
                {'template': 'Choose Student information, Enrollment history, Opening balances, or Fee history.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        names = {
            'student_information': 'student-information',
            'enrollment_history': 'enrollment-history',
            'opening_balances': 'opening-balances',
            'historical_charges': 'historical-charges',
            'historical_payments': 'historical-payments',
        }
        if request.query_params.get('file') == 'csv':
            from migration.services.templates import build_template_csv
            response = HttpResponse(build_template_csv(template), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{names[template]}.csv"'
            return response
        response = HttpResponse(
            build_template_xlsx(template),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{names[template]}.xlsx"'
        return response


class MigrationClassResolutionView(MigrationJobDetailView):
    def get(self, request, job_id):
        return Response({'classes': class_groups(self._job(job_id))})

    def post(self, request, job_id):
        job = self._job(job_id)
        confirm_class_value(
            job=job,
            actor=request.user,
            source_value=request.data.get('source_value', ''),
            stream_id=request.data.get('stream_id', ''),
            use_snapshot=bool(request.data.get('use_snapshot')),
        )
        plan_for_job(job)
        return Response({'classes': class_groups(job)})


class MigrationValueReconciliationView(MigrationJobDetailView):
    def get(self, request, job_id):
        return Response({'fields': value_groups(self._job(job_id))})

    def post(self, request, job_id):
        job = self._job(job_id)
        items = request.data.get('values', [])
        if not isinstance(items, list) or not items:
            return Response({'values': 'Choose at least one value.'}, status=status.HTTP_400_BAD_REQUEST)
        approve_values(job=job, actor=request.user, items=items)
        plan_for_job(job)
        return Response({'fields': value_groups(job)})
