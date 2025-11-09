from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError
from .models import Student


def student_login(request):
    """Student login view"""
    # If already logged in, redirect to dashboard
    if request.session.get('student_id'):
        return redirect('student_dashboard')

    if request.method == 'POST':
        usn = request.POST.get('usn', '').strip().upper()
        password = request.POST.get('password', '')

        try:
            # Find student by USN
            student = Student.objects.get(usn=usn, is_active=True)

            # Check password
            if student.check_password(password):
                # Set session
                request.session['student_id'] = student.student_id
                request.session['student_usn'] = student.usn
                request.session['student_name'] = student.get_full_name()
                request.session['user_type'] = 'student'

                messages.success(request, f'Welcome back, {student.first_name}!')
                return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid USN or password')

        except Student.DoesNotExist:
            messages.error(request, 'Invalid USN or password')

    return render(request, 'students/login.html')


def student_register(request):
    """Student registration view"""
    # If already logged in, redirect to dashboard
    if request.session.get('student_id'):
        return redirect('student_dashboard')

    if request.method == 'POST':
        # Get form data
        usn = request.POST.get('usn', '').strip().upper()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        department = request.POST.get('department', '')
        semester = request.POST.get('semester', '')
        gender = request.POST.get('gender', '')
        date_of_birth = request.POST.get('date_of_birth', '')
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if not all([usn, first_name, last_name, email, department, semester, password]):
            messages.error(request, 'Please fill all required fields')
            return render(request, 'students/register.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'students/register.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'students/register.html')

        try:
            # Create student
            student = Student(
                usn=usn,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone if phone else None,
                department=department,
                semester=int(semester),
                gender=gender if gender else None,
                date_of_birth=date_of_birth if date_of_birth else None,
                address=address if address else None
            )

            # Set password (will be hashed)
            student.set_password(password)

            # Save to database
            student.save()

            messages.success(request, 'Registration successful! Please login to continue.')
            return redirect('student_login')

        except IntegrityError as e:
            if 'usn' in str(e).lower():
                messages.error(request, 'USN already exists. Please use a different USN.')
            elif 'email' in str(e).lower():
                messages.error(request, 'Email already exists. Please use a different email.')
            else:
                messages.error(request, 'Registration failed. Please try again.')

        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    return render(request, 'students/register.html')


def student_logout(request):
    """Student logout view"""
    # Clear session
    if 'student_id' in request.session:
        del request.session['student_id']
    if 'student_usn' in request.session:
        del request.session['student_usn']
    if 'student_name' in request.session:
        del request.session['student_name']
    if 'user_type' in request.session:
        del request.session['user_type']

    messages.success(request, 'You have been logged out successfully')
    return redirect('student_login')


def student_dashboard(request):
    """Student dashboard view"""
    # Check if logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to access dashboard')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    context = {
        'student': student
    }

    return render(request, 'students/dashboard.html', context)


def student_profile(request):
    """View and edit student profile"""
    # Check if logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to access profile')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            phone = request.POST.get('phone', '').strip()
            department = request.POST.get('department', '')
            semester = request.POST.get('semester', '')
            gender = request.POST.get('gender', '')
            date_of_birth = request.POST.get('date_of_birth', '')
            address = request.POST.get('address', '').strip()

            # Validation
            if not all([first_name, last_name, email, department, semester]):
                messages.error(request, 'Please fill all required fields')
                return redirect('student_profile')

            # Check if email already exists for another student
            if Student.objects.exclude(student_id=student_id).filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('student_profile')

            # Update student
            student.first_name = first_name
            student.last_name = last_name
            student.email = email
            student.phone = phone if phone else None
            student.department = department
            student.semester = int(semester)
            student.gender = gender if gender else None
            student.date_of_birth = date_of_birth if date_of_birth else None
            student.address = address if address else None

            student.save()

            # Update session name
            request.session['student_name'] = student.get_full_name()

            messages.success(request, 'Profile updated successfully!')
            return redirect('student_profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    context = {
        'student': student
    }

    return render(request, 'students/profile.html', context)


def student_change_password(request):
    """Change student password"""
    # Check if logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to change password')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, 'All fields are required')
            return redirect('student_change_password')

        # Check current password
        if not student.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('student_change_password')

        # Check new password length
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long')
            return redirect('student_change_password')

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('student_change_password')

        # Update password
        student.set_password(new_password)
        student.save()

        messages.success(request, 'Password changed successfully!')
        return redirect('student_dashboard')

    context = {
        'student': student
    }

    return render(request, 'students/change_password.html', context)