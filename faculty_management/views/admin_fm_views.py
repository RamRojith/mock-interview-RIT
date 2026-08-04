from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from user_accounts.decorators import no_cache, is_super_user
from faculty_management.models import (
    SeminarHall, SHBApprovalWorkflow, SHBApprovalStep, 
    SeminarHallBooking, SHBApplicationApproval
)
from user_accounts.models import Add_Department, Role, USER
from django.db.models import Q
import json
from datetime import datetime


@no_cache
@is_super_user('admin_management')
def manage_seminar_halls(request):
    """Manage Seminar Halls - Add, Edit, Delete"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            try:
                SeminarHall.objects.create(
                    hall_name=request.POST.get('hall_name'),
                    hall_number=request.POST.get('hall_number'),
                    capacity=request.POST.get('capacity', 0) or 0,
                    has_projector=request.POST.get('has_projector') == 'on',
                    has_sound_system=request.POST.get('has_sound_system') == 'on',
                    has_ac=request.POST.get('has_ac') == 'on',
                )
                messages.success(request, 'Seminar Hall added successfully!')
            except Exception as e:
                messages.error(request, f'Error adding hall: {str(e)}')
        
        elif action == 'edit':
            try:
                hall = get_object_or_404(SeminarHall, id=request.POST.get('hall_id'))
                
                hall.hall_name = request.POST.get('hall_name')
                hall.hall_number = request.POST.get('hall_number')
                hall.capacity = request.POST.get('capacity', 0) or 0
                hall.has_projector = request.POST.get('has_projector') == 'on'
                hall.has_sound_system = request.POST.get('has_sound_system') == 'on'
                hall.has_ac = request.POST.get('has_ac') == 'on'
                hall.save()
                messages.success(request, 'Seminar Hall updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating hall: {str(e)}')
        
        elif action == 'delete':
            try:
                hall = get_object_or_404(SeminarHall, id=request.POST.get('hall_id'))
                hall.delete()
                messages.success(request, 'Seminar Hall deleted successfully!')
            except Exception as e:
                messages.error(request, f'Error deleting hall: {str(e)}')
        
        return redirect('manage_seminar_halls')
    
    halls = SeminarHall.objects.all().order_by('hall_number')
    
    context = {
        'halls': halls,
    }
    
    return render(request, 'faculty_management/admin/manage_seminar_halls.html', context)


@no_cache
@is_super_user('admin_management')
def shb_approval_hierarchy(request):
    """Manage Seminar Hall Booking Approval Hierarchy - Creator Role Based"""
    
    roles = Role.objects.using('rit_approval_system').all().order_by('role')
    departments = Add_Department.objects.all().order_by('Department')
    
    context = {
        'roles': roles,
        'departments': departments,
    }
    
    return render(request, 'faculty_management/admin/shb_approval_hierarchy.html', context)


def get_shb_workflow_roles(request, creator_role_id):
    """API endpoint to get workflow roles for a creator role"""
    if request.method == 'GET':
        try:
            # Convert to integer
            try:
                creator_role_id = int(creator_role_id)
            except (ValueError, TypeError) as e:
                return JsonResponse({'error': f'Invalid creator role ID: {creator_role_id}'}, status=400)
            
            # Verify creator role exists
            try:
                creator_role = Role.objects.using('rit_approval_system').get(id=creator_role_id)
            except Role.DoesNotExist:
                return JsonResponse({'error': 'Creator role not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
            
            # Get all roles except the creator role
            try:
                all_roles = Role.objects.using('rit_approval_system').exclude(id=creator_role_id)
            except Exception as e:
                return JsonResponse({'error': f'Database error fetching roles: {str(e)}'}, status=500)
            
            # Find existing workflow for this creator role
            try:
                workflow = SHBApprovalWorkflow.objects.filter(created_by_id=creator_role_id).first()
            except Exception as e:
                return JsonResponse({'error': f'Database error fetching workflow: {str(e)}'}, status=500)
            
            matched_roles = []
            matched_ids = []
            
            if workflow:
                # Get approval steps for this workflow
                try:
                    steps = workflow.steps.all().order_by('approval_level')
                    
                    for step in steps:
                        try:
                            role = Role.objects.using('rit_approval_system').get(id=step.approver_role_id)
                            matched_roles.append({
                                'id': role.id,
                                'name': role.role,
                                'is_cross_department': step.is_cross_department,
                                'approver_department_id': step.approver_department_id
                            })
                            matched_ids.append(role.id)
                        except Role.DoesNotExist:
                            continue
                        except Exception as e:
                            continue
                except Exception as e:
                    return JsonResponse({'error': f'Database error fetching steps: {str(e)}'}, status=500)
            
            # Get unmatched roles
            try:
                if matched_ids:
                    unmatched_roles = [
                        {'id': r.id, 'name': r.role}
                        for r in all_roles.exclude(id__in=matched_ids)
                    ]
                else:
                    unmatched_roles = [
                        {'id': r.id, 'name': r.role}
                        for r in all_roles
                    ]
            except Exception as e:
                return JsonResponse({'error': f'Error building roles list: {str(e)}'}, status=500)
            
            return JsonResponse({
                'matched_roles': matched_roles,
                'unmatched_roles': unmatched_roles
            })
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            # print(f"Error in get_shb_workflow_roles: {str(e)}")
            # print(error_trace)
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_POST
def save_shb_workflow(request):
    """Save seminar hall booking approval workflow"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            creator_role_id = data.get('creatorRole')
            role_hierarchy = data.get('roleHierarchy', [])
            
            # Validate creator role
            if not creator_role_id:
                return JsonResponse({'error': 'Creator role is required'}, status=400)
            
            # Verify creator role exists
            try:
                creator_role = Role.objects.using('rit_approval_system').get(id=creator_role_id)
            except Role.DoesNotExist:
                return JsonResponse({'error': 'Creator role not found'}, status=404)
            
            # Validate role hierarchy
            if not role_hierarchy or len(role_hierarchy) == 0:
                return JsonResponse({'error': 'Role hierarchy cannot be empty'}, status=400)
            
            # Get or create workflow
            workflow, created = SHBApprovalWorkflow.objects.get_or_create(
                created_by_id=creator_role_id,
                defaults={
                    'workflow_name': f"Seminar Hall Booking - {creator_role.role}",
                    'is_active': True
                }
            )
            
            # If not created, update workflow name
            if not created:
                workflow.workflow_name = f"Seminar Hall Booking - {creator_role.role}"
                workflow.save()
            
            # Delete existing steps
            workflow.steps.all().delete()
            
            # Create new steps
            for index, hierarchy_item in enumerate(role_hierarchy):
                approver_role_id = hierarchy_item.get('id')
                is_cross_department = hierarchy_item.get('isCrossDepartment', False)
                department_id = hierarchy_item.get('departmentId')
                
                # Verify approver role exists
                try:
                    approver_role = Role.objects.using('rit_approval_system').get(id=approver_role_id)
                except Role.DoesNotExist:
                    return JsonResponse({'error': f'Approver role with ID {approver_role_id} not found'}, status=404)
                
                # Verify department if cross-department
                if is_cross_department and department_id:
                    try:
                        Add_Department.objects.get(id=department_id)
                    except Add_Department.DoesNotExist:
                        return JsonResponse({'error': f'Department with ID {department_id} not found'}, status=404)
                
                # Create approval step
                SHBApprovalStep.objects.create(
                    workflow=workflow,
                    approval_level=index + 1,
                    approver_role_id=approver_role_id,
                    is_cross_department=is_cross_department,
                    approver_department_id=department_id if is_cross_department else None,
                    is_active=True
                )
            
            return JsonResponse({
                'message': f'Workflow configuration saved successfully for {creator_role.role}!',
                'workflow_id': workflow.id,
                'workflow_name': workflow.workflow_name,
                'steps_count': len(role_hierarchy)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            import traceback
            # print(f"Error in save_shb_workflow: {str(e)}")
            # print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@no_cache
@is_super_user('admin_management')
def shb_applications(request):
    """View all Seminar Hall Booking Applications"""
    
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    applications = SeminarHallBooking.objects.all().select_related(
        'faculty', 'department'
    ).order_by('-created_at')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    if department_filter:
        applications = applications.filter(department_id=department_filter)
    
    departments = Add_Department.objects.all().order_by('Department')
    
    context = {
        'applications': applications,
        'departments': departments,
        'status_filter': status_filter,
        'department_filter': department_filter,
    }
    
    return render(request, 'faculty_management/admin/shb_applications.html', context)


@no_cache
def shb_application_detail(request, booking_id):
    """View detailed information about a booking application"""
    
    application = get_object_or_404(
        SeminarHallBooking.objects.select_related('faculty', 'department'),
        booking_id=booking_id
    )
    
    # Get approval history
    approvals = SHBApplicationApproval.objects.filter(
        application=application
    ).select_related('approval_step', 'approver').order_by('approval_step__approval_level')
    
    context = {
        'application': application,
        'approvals': approvals,
    }
    
    return render(request, 'faculty_management/admin/shb_application_detail.html', context)


def can_user_approve_shb(user, application):
    """Check if user can approve the seminar hall booking application"""
    try:
        # Get user's role and department
        user_role_id = user.role_id
        user_dept_id = user.Department_id
        
        # Get pending approvals for this application
        pending_approvals = SHBApplicationApproval.objects.filter(
            application=application,
            status='pending'
        ).select_related('approval_step').order_by('approval_step__approval_level')
        
        if not pending_approvals.exists():
            return False
        
        # Get the first pending approval (current level)
        current_approval = pending_approvals.first()
        step = current_approval.approval_step
        
        # Check if user's role matches
        if step.approver_role_id != user_role_id:
            return False
        
        # Check department match
        if step.is_cross_department:
            # Cross-department approver can approve any application
            return True
        else:
            # Department-specific approver
            if step.approver_department_id:
                return step.approver_department_id == user_dept_id
            else:
                # If no specific department, match with application department
                return application.department_id == user_dept_id
        
        return False
    except Exception as e:
        # print(f"Error checking approval permission: {e}")
        return False


@require_POST
def approve_shb_application(request, booking_id):
    """Approve or reject a seminar hall booking application"""
    try:
        application = get_object_or_404(SeminarHallBooking, booking_id=booking_id)
        action = request.POST.get('action')  # 'approve' or 'reject'
        comments = request.POST.get('comments', '')
        
        # Check if user can approve
        if not can_user_approve_shb(request.user, application):
            messages.error(request, 'You do not have permission to approve this application.')
            return redirect('shb_application_detail', booking_id=booking_id)
        
        # Get current pending approval
        current_approval = SHBApplicationApproval.objects.filter(
            application=application,
            status='pending'
        ).select_related('approval_step').order_by('approval_step__approval_level').first()
        
        if not current_approval:
            messages.error(request, 'No pending approval found.')
            return redirect('shb_application_detail', booking_id=booking_id)
        
        if action == 'approve':
            current_approval.status = 'approved'
            current_approval.approver = request.user
            current_approval.comments = comments
            current_approval.approved_at = datetime.now()
            current_approval.save()
            
            # Check if there are more pending approvals
            remaining_pending = SHBApplicationApproval.objects.filter(
                application=application,
                status='pending'
            ).exists()
            
            if not remaining_pending:
                # All approvals done - mark application as approved
                application.status = 'approved'
                application.approved_by = request.user
                application.approval_date = datetime.now()
                application.save()
                messages.success(request, 'Application approved successfully! All approvals completed.')
            else:
                messages.success(request, 'Application approved at your level. Pending further approvals.')
        
        elif action == 'reject':
            current_approval.status = 'rejected'
            current_approval.approver = request.user
            current_approval.comments = comments
            current_approval.approved_at = datetime.now()
            current_approval.save()
            
            # Mark application as rejected
            application.status = 'rejected'
            application.rejection_reason = comments
            application.save()
            
            messages.success(request, 'Application rejected successfully.')
        
        return redirect('shb_application_detail', booking_id=booking_id)
        
    except Exception as e:
        messages.error(request, f'Error processing approval: {str(e)}')
        return redirect('shb_application_detail', booking_id=booking_id)
